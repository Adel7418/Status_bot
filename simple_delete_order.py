#!/usr/bin/env python3
"""
Simple script to delete orders with LONG_REPAIR status
"""

import asyncio
import sys
from pathlib import Path


# Add project path
sys.path.append(str(Path(__file__).parent))

from app.config import OrderStatus
from app.database import Database


async def delete_order(order_id: int):
    """Delete order with LONG_REPAIR status"""
    db = Database()
    await db.connect()

    try:
        # Get order
        order = await db.get_order_by_id(order_id)

        if not order:
            print(f"Order #{order_id} not found")
            return False

        print(f"Order #{order_id}:")
        print(f"  Client: {order.client_name}")
        print(f"  Equipment: {order.equipment_type}")
        print(f"  Status: {order.status}")

        # Confirmation
        confirm = input(f"\nAre you sure you want to delete order #{order_id}? (yes/no): ")

        if confirm.lower() not in ["yes", "y"]:
            print("Deletion cancelled")
            return False

        # Soft delete order
        success = await db.soft_delete_order(order_id)

        if success:
            print(f"Order #{order_id} successfully deleted")

            # Add to audit
            await db.add_audit_log(
                user_id=0,  # System action
                action="DELETE_ORDER_SCRIPT",
                details=f"Order #{order_id} with LONG_REPAIR status deleted by script",
            )

            return True
        else:
            print(f"Error deleting order #{order_id}")
            return False

    except Exception as e:
        print(f"Error: {e}")
        return False

    finally:
        await db.disconnect()


async def list_orders():
    """List orders with LONG_REPAIR status"""
    db = Database()
    await db.connect()

    try:
        # Get all orders with DR status using SQL
        async with db.get_session() as session:
            from sqlalchemy import text

            result = await session.execute(
                text(
                    "SELECT id, client_name, equipment_type, description, created_at FROM orders WHERE status = :status"
                ),
                {"status": OrderStatus.DR},
            )
            orders = result.fetchall()

        if not orders:
            print("No orders with LONG_REPAIR status found")
            return

        print(f"Found {len(orders)} orders with LONG_REPAIR status:\n")

        for order in orders:
            print(f"Order #{order.id}:")
            print(f"  Client: {order.client_name}")
            print(f"  Equipment: {order.equipment_type}")
            print(f"  Created: {order.created_at}")
            print()

    except Exception as e:
        print(f"Error getting orders: {e}")

    finally:
        await db.disconnect()


async def main():
    """Main function"""
    print("Script for deleting orders with LONG_REPAIR status\n")

    if len(sys.argv) > 1:
        # Delete specific order
        try:
            order_id = int(sys.argv[1])
            await delete_order(order_id)
        except ValueError:
            print("Invalid order ID. Use a number.")
    else:
        # Show list of orders
        await list_orders()
        print("\nTo delete specific order use:")
        print("   python simple_delete_order.py <ORDER_ID>")


if __name__ == "__main__":
    asyncio.run(main())
