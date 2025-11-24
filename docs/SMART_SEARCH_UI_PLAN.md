# Smart Search UI & Workflow Plan

## 1. Overview
The goal is to simplify the "Order Search" feature by removing unnecessary sub-menus. Instead of asking the user to choose between "Phone", "Address", or "ID", we provide a **single input field** that intelligently detects the search criteria.

## 2. User Flow & UI Mockups

### Step 1: Search Entry
User clicks "🔍 Поиск заказов" in the main menu.

**Bot Message:**
> 🔍 **Поиск заказов**
>
> Введите **ID заказа**, **номер телефона** или **адрес**:
> *(система сама определит тип данных)*

**Keyboard:**
| ❌ Отмена |

---

### Step 2: Input Processing (Smart Search)
The system analyzes the input with improved detection logic:

**Priority Rules:**
1. **Contains letters** → Treated as **Address**
2. **Valid phone format** (11 digits 7/8...) → Treated as **Phone Number**
3. **Contains spaces/punctuation** (e.g., "15 а", "42-1") → Treated as **Address**
4. **Pure digits** with intelligent fallback:
   - **1-4 digits:** Try **Order ID** → fallback to **Address** (house/apartment numbers)
   - **5-6 digits:** Try **Order ID** → fallback to **Address**
   - **7-9 digits:** Try **Order ID** (if <1 million) → fallback to **Address**
   - **10+ digits:** Treated as **Address** (cannot be Order ID)

**Examples:**
- `"15"` → Try Order #15, if not found → search addresses with "15"
- `"Ленина 15"` → Address (contains letters)
- `"79991234567"` → Phone (valid format)
- `"123"` → Try Order #123, if not found → search addresses

---

### Step 3: Search Results (List View)
If multiple orders are found (e.g., search by phone or common address).

**Bot Message:**
> 🔍 **Результаты поиска**
> Запрос: *+79991234567*
> Найдено: **3**
>
> Выберите заказ для просмотра:

**Keyboard:**
| #1234 | Стиральная машина | ⏳ |
| #1230 | Холодильник | ✅ |
| #1105 | Плита | ❌ |
| ⬅️ | 1/1 | ➡️ |
| 🔙 Новый поиск |

---

### Step 4: Order Details (Card View)
User clicks on a specific order (e.g., #1234).

**Bot Message:**
> 📄 **Заказ #1234**
>
> 👤 **Клиент:** Иван Иванов
> 📱 **Телефон:** +7 (999) 123-45-67
> 🏠 **Адрес:** ул. Ленина, д. 1, кв. 10
> 🔧 **Техника:** Стиральная машина LG
> 📝 **Проблема:** Не сливает воду
>
> 💰 **Сумма:** 5000 руб.
> 👨‍🔧 **Мастер:** Петр Петров
> ⏳ **Статус:** В работе
> 📅 **Создан:** 25.11.2025 10:00

**Keyboard:**
| ✏️ Редактировать |
| 🔙 К списку | 🔍 Новый поиск |

---

## 3. Technical Implementation Details (Already Applied)

### 1. Unified State
*   Removed: `enter_phone`, `enter_address`, `select_search_type`
*   Added: `SearchOrderStates.enter_query`

### 2. Smart Service Logic (`OrderSearchService`)
*   `unified_search(query)` method with improved detection logic.
*   Automatically normalizes phone numbers.
*   Intelligently detects Order IDs with fallback to address search.
*   Handles edge cases: digit-only addresses (house numbers), spaces/punctuation.
*   Returns tuple: (list of orders, search type description).

### 3. Handlers (`handlers/order_search.py`)
*   Single handler `process_search_query` replaces multiple specific handlers.
*   Implements pagination logic for results.
*   Uses FSM to store search results temporarily for navigation.

## 4. Implementation Status

### ✅ Completed (2025-11-25)
* Improved `unified_search()` detection logic with fallback for digit-only addresses
* Cleaned up legacy FSM states (removed 4 unused states)
* Enhanced user messages with smart suggestions when no results found
* Updated initial prompt with clear examples and tips
* Added `search_order_by_id()` method for ID-based search
* Updated documentation to reflect actual implementation

### 🔄 Future Refinements (Optional)
*   [ ] Add "Search by Master" filter
*   [ ] Add "Search by Date" filter
*   [ ] Implement fuzzy address matching (Levenshtein distance)
*   [ ] Add search history feature
