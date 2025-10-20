"""
Middleware для ограничения частоты запросов (Rate Limiting)
"""

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypedDict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message


logger = logging.getLogger(__name__)


class RateLimitBucket(TypedDict):
    """Структура данных для хранения информации о rate limiting для пользователя"""

    tokens: float
    last_update: float
    violations: int
    violation_timestamps: list[float]
    banned_until: float | None
    last_warning_sent: float


class RateLimitMiddleware(BaseMiddleware):
    """
    Middleware для защиты от spam и DoS атак

    Использует алгоритм Token Bucket для ограничения частоты запросов
    """

    def __init__(
        self,
        rate: int = 3,  # Запросов в период
        period: int = 1,  # Период в секундах
        burst: int = 5,  # Максимальный burst (всплеск)
        max_violations: int = 30,  # Максимум нарушений перед баном
        violation_window: int = 60,  # Окно для подсчёта нарушений (секунды)
    ):
        """
        Инициализация Rate Limiter

        Args:
            rate: Количество разрешённых запросов в период
            period: Период в секундах
            burst: Максимальный burst (сколько запросов можно сделать сразу)
            max_violations: Максимум нарушений перед постоянной блокировкой
            violation_window: Окно времени для подсчёта нарушений (секунды)

        Пример:
            rate=3, period=1, burst=5
            → 3 запроса в секунду, но можно сделать до 5 подряд
        """
        super().__init__()
        self.rate = rate
        self.period = period
        self.burst = burst
        self.max_violations = max_violations
        self.violation_window = violation_window

        # Хранилище для каждого пользователя
        self.buckets: dict[int, RateLimitBucket] = {}

    def _get_tokens(self, user_id: int) -> float:
        """
        Получить текущее количество доступных токенов для пользователя

        Args:
            user_id: Telegram ID пользователя

        Returns:
            Количество доступных токенов
        """
        now = time.time()

        if user_id not in self.buckets:
            # Новый пользователь - даём полный burst
            self.buckets[user_id] = {
                "tokens": float(self.burst),
                "last_update": now,
                "violations": 0,
                "violation_timestamps": [],
                "banned_until": None,
                "last_warning_sent": 0,  # Timestamp последнего предупреждения
            }
            return float(self.burst)

        bucket = self.buckets[user_id]

        # Вычисляем сколько токенов восстановилось
        time_passed = now - bucket["last_update"]
        tokens_to_add = time_passed * (self.rate / self.period)

        # Обновляем количество токенов (не больше burst)
        new_tokens = min(self.burst, bucket["tokens"] + tokens_to_add)
        bucket["tokens"] = new_tokens
        bucket["last_update"] = now

        return float(new_tokens)

    def _clean_old_violations(self, user_id: int) -> int:
        """
        Очистить старые нарушения вне временного окна

        Args:
            user_id: Telegram ID пользователя

        Returns:
            Количество актуальных нарушений
        """
        if user_id not in self.buckets:
            return 0

        now = time.time()
        bucket = self.buckets[user_id]

        # Фильтруем нарушения - оставляем только те, что в пределах окна
        cutoff_time = now - self.violation_window
        bucket["violation_timestamps"] = [
            ts for ts in bucket["violation_timestamps"] if ts > cutoff_time
        ]

        # Обновляем счетчик
        violations_count = len(bucket["violation_timestamps"])
        bucket["violations"] = violations_count

        return violations_count

    def _add_violation(self, user_id: int) -> int:
        """
        Зарегистрировать нарушение

        Args:
            user_id: Telegram ID пользователя

        Returns:
            Текущее количество нарушений
        """
        now = time.time()
        bucket = self.buckets[user_id]

        # Добавляем timestamp нарушения
        bucket["violation_timestamps"].append(now)
        violations_count = len(bucket["violation_timestamps"])
        bucket["violations"] = violations_count

        # Проверяем, не превысили ли лимит
        if violations_count >= self.max_violations:
            # Постоянный бан на 1 час
            bucket["banned_until"] = now + 3600
            logger.critical(
                f"🚫 User {user_id} PERMANENTLY BANNED for {self.max_violations}+ violations"
            )

        return violations_count

    def _consume_token(self, user_id: int) -> bool:
        """
        Попытка использовать токен

        Args:
            user_id: Telegram ID пользователя

        Returns:
            True если токен доступен и использован
        """
        tokens = self._get_tokens(user_id)

        if tokens >= 1:
            self.buckets[user_id]["tokens"] -= 1
            return True

        return False

    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        """
        Обработка события с проверкой rate limit

        Args:
            handler: Следующий handler
            event: Событие (Message или CallbackQuery)
            data: Данные

        Returns:
            Результат выполнения handler или None если превышен лимит
        """
        user = event.from_user

        if not user:
            # Нет пользователя - пропускаем
            return await handler(event, data)

        user_id = user.id
        now = time.time()

        # Получаем или создаём bucket
        if user_id not in self.buckets:
            self._get_tokens(user_id)

        bucket = self.buckets[user_id]

        # Убеждаемся, что у bucket есть поле last_warning_sent (для обратной совместимости)
        if "last_warning_sent" not in bucket:
            bucket["last_warning_sent"] = 0

        # Проверяем, не забанен ли пользователь
        if bucket.get("banned_until") and bucket["banned_until"] > now:
            remaining_ban = int(bucket["banned_until"] - now)

            # Проверяем, нужно ли отправлять предупреждение
            # Отправляем максимум раз в 10 секунд для забаненных
            last_warning = bucket.get("last_warning_sent", 0)
            should_send_warning = (now - last_warning) >= 10

            if should_send_warning:
                logger.error(
                    f"🚫 BANNED user {user_id} (@{user.username}) tried to access. "
                    f"Ban remaining: {remaining_ban}s"
                )

                if isinstance(event, Message):
                    await event.answer(
                        f"🚫 <b>ВЫ ЗАБЛОКИРОВАНЫ</b>\n\n"
                        f"Причина: Чрезмерный спам ({self.max_violations}+ нарушений)\n"
                        f"Блокировка истекает через: {remaining_ban // 60} мин {remaining_ban % 60} сек\n\n"
                        f"<i>Дальнейшие сообщения игнорируются.</i>",
                        parse_mode="HTML",
                    )
                elif isinstance(event, CallbackQuery):
                    await event.answer(
                        f"🚫 Вы заблокированы за спам на {remaining_ban // 60} мин", show_alert=True
                    )

                bucket["last_warning_sent"] = now
            else:
                # Молча блокируем без ответа
                logger.debug(f"🚫 BANNED user {user_id} blocked silently (warning cooldown)")

            return None

        # Если бан истёк - сбрасываем
        if bucket.get("banned_until") and bucket["banned_until"] <= now:
            bucket["banned_until"] = None
            bucket["violations"] = 0
            bucket["violation_timestamps"] = []
            logger.info(f"✅ Ban expired for user {user_id}. Reset violations.")

        # Очищаем старые нарушения
        self._clean_old_violations(user_id)

        # Проверяем лимит токенов
        if not self._consume_token(user_id):
            # Лимит превышен - регистрируем нарушение
            violations = self._add_violation(user_id)
            current_tokens = bucket["tokens"]

            # Рассчитываем базовое время ожидания
            tokens_needed = 1.0 - current_tokens
            base_wait_time = max(10, int((tokens_needed / self.rate) * self.period))

            # Прогрессивное наказание за нарушения
            if violations <= 3:
                wait_time = base_wait_time
            elif violations <= 10:
                # 4-10 нарушений: × 2-5
                wait_time = base_wait_time * min(violations - 1, 5)
            elif violations <= 20:
                # 11-20 нарушений: × 6-15
                wait_time = base_wait_time * (violations - 5)
            else:
                # 21-29 нарушений: × 20-30
                wait_time = base_wait_time * (violations)

            # Проверяем, нужно ли отправлять предупреждение
            # Отправляем максимум раз в 5 секунд
            last_warning = bucket.get("last_warning_sent", 0)
            should_send_warning = (now - last_warning) >= 5

            if should_send_warning:
                logger.warning(
                    f"⚠️ Rate limit exceeded for user {user_id} (@{user.username}). "
                    f"Wait time: {wait_time}s, violations: {violations}/{self.max_violations}, tokens: {current_tokens:.2f}"
                )

                # Отправляем сообщение пользователю
                if isinstance(event, Message):
                    warning_text = (
                        f"⚠️ <b>Слишком много запросов</b>\n\n"
                        f"Подождите {wait_time} сек. и попробуйте снова.\n\n"
                    )

                    if violations > 5:
                        warning_text += (
                            f"🔴 <b>ВНИМАНИЕ: Обнаружен спам!</b>\n"
                            f"Нарушений: {violations}/{self.max_violations}\n"
                            f"Время блокировки прогрессивно увеличено.\n\n"
                        )

                    if violations > 20:
                        warning_text += (
                            f"⚠️ <b>ПОСЛЕДНЕЕ ПРЕДУПРЕЖДЕНИЕ!</b>\n"
                            f"При достижении {self.max_violations} нарушений - бан на 1 час!\n\n"
                        )

                    warning_text += "<i>Дальнейшие сообщения игнорируются.</i>"

                    await event.answer(warning_text, parse_mode="HTML")
                elif isinstance(event, CallbackQuery):
                    await event.answer(
                        f"⚠️ Слишком много запросов. Подождите {wait_time} сек.\nНарушений: {violations}/{self.max_violations}",
                        show_alert=True,
                    )

                bucket["last_warning_sent"] = now
            else:
                # Молча блокируем без ответа
                logger.debug(
                    f"⚠️ User {user_id} rate limited silently. "
                    f"Violations: {violations}/{self.max_violations} (warning cooldown)"
                )

            # НЕ вызываем handler - блокируем запрос
            return None

        # Лимит не превышен - пропускаем запрос
        logger.debug(
            f"Rate limit OK for user {user_id}. "
            f"Remaining tokens: {bucket['tokens']:.2f}, violations: {bucket['violations']}"
        )

        return await handler(event, data)

    def get_stats(self) -> dict:
        """
        Получить статистику по rate limiting

        Returns:
            Словарь со статистикой
        """
        banned_users = sum(
            1
            for bucket in self.buckets.values()
            if bucket.get("banned_until") and bucket["banned_until"] > time.time()
        )

        users_with_violations = sum(
            1 for bucket in self.buckets.values() if bucket.get("violations", 0) > 0
        )

        return {
            "total_users": len(self.buckets),
            "banned_users": banned_users,
            "users_with_violations": users_with_violations,
            "rate": self.rate,
            "period": self.period,
            "burst": self.burst,
            "max_violations": self.max_violations,
            "violation_window": self.violation_window,
        }
