from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import config
from database.models import (
    CartItem,
    Category,
    MenuItem,
    Order,
    OrderItem,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    User,
)


# ---------- Пользователи ----------

async def get_or_create_user(session: AsyncSession, telegram_id: int, username: str | None,
                              full_name: str | None) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
            is_admin=telegram_id in config.admin_ids,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    else:
        # Пользователей из ADMIN_IDS всегда подтягиваем в админы автоматически.
        # Обратное (убрать права) НЕ делаем здесь: права также могут быть
        # выданы через вход по логину/паролю (см. handlers/admin/auth.py),
        # и выход из системы обрабатывается отдельно через set_user_admin().
        if telegram_id in config.admin_ids and not user.is_admin:
            user.is_admin = True
            await session.commit()
    return user


async def set_user_admin(session: AsyncSession, user_id: int, is_admin: bool) -> None:
    await session.execute(update(User).where(User.id == user_id).values(is_admin=is_admin))
    await session.commit()


async def update_user_contact(session: AsyncSession, user_id: int, phone: str | None = None,
                               address: str | None = None) -> None:
    values = {}
    if phone is not None:
        values["phone"] = phone
    if address is not None:
        values["last_address"] = address
    if values:
        await session.execute(update(User).where(User.id == user_id).values(**values))
        await session.commit()


async def complete_registration(session: AsyncSession, user_id: int, full_name: str,
                                 phone: str, address: str) -> None:
    await session.execute(
        update(User).where(User.id == user_id).values(
            full_name=full_name,
            phone=phone,
            last_address=address,
            is_registered=True,
        )
    )
    await session.commit()


# ---------- Категории и меню ----------

async def get_active_categories(session: AsyncSession) -> list[Category]:
    result = await session.execute(
        select(Category).where(Category.is_active == True).order_by(Category.sort_order, Category.id)  # noqa: E712
    )
    return list(result.scalars().all())


async def get_all_categories(session: AsyncSession) -> list[Category]:
    result = await session.execute(select(Category).order_by(Category.sort_order, Category.id))
    return list(result.scalars().all())


async def get_category(session: AsyncSession, category_id: int) -> Category | None:
    return await session.get(Category, category_id)


async def create_category(session: AsyncSession, name: str) -> Category:
    category = Category(name=name)
    session.add(category)
    await session.commit()
    await session.refresh(category)
    return category


async def rename_category(session: AsyncSession, category_id: int, name: str) -> None:
    await session.execute(update(Category).where(Category.id == category_id).values(name=name))
    await session.commit()


async def delete_category(session: AsyncSession, category_id: int) -> None:
    category = await session.get(Category, category_id)
    if category:
        await session.delete(category)
        await session.commit()


async def get_items_by_category(session: AsyncSession, category_id: int) -> list[MenuItem]:
    result = await session.execute(
        select(MenuItem)
        .where(MenuItem.category_id == category_id)
        .order_by(MenuItem.sort_order, MenuItem.id)
    )
    return list(result.scalars().all())


async def get_item(session: AsyncSession, item_id: int) -> MenuItem | None:
    return await session.get(MenuItem, item_id)


async def create_item(session: AsyncSession, category_id: int, name: str, description: str | None,
                       price: float) -> MenuItem:
    item = MenuItem(category_id=category_id, name=name, description=description, price=price)
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


async def update_item_availability(session: AsyncSession, item_id: int, is_available: bool) -> None:
    await session.execute(update(MenuItem).where(MenuItem.id == item_id).values(is_available=is_available))
    await session.commit()


async def update_item_photo(session: AsyncSession, item_id: int, photo_file_id: str) -> None:
    await session.execute(update(MenuItem).where(MenuItem.id == item_id).values(photo_file_id=photo_file_id))
    await session.commit()


async def update_item_fields(session: AsyncSession, item_id: int, **fields) -> None:
    if fields:
        await session.execute(update(MenuItem).where(MenuItem.id == item_id).values(**fields))
        await session.commit()


async def delete_item(session: AsyncSession, item_id: int) -> None:
    item = await session.get(MenuItem, item_id)
    if item:
        await session.delete(item)
        await session.commit()


# ---------- Корзина ----------

async def get_cart(session: AsyncSession, user_id: int) -> list[CartItem]:
    result = await session.execute(
        select(CartItem)
        .options(selectinload(CartItem.menu_item))
        .where(CartItem.user_id == user_id)
    )
    return list(result.scalars().all())


async def add_to_cart(session: AsyncSession, user_id: int, item_id: int, quantity: int = 1) -> None:
    result = await session.execute(
        select(CartItem).where(CartItem.user_id == user_id, CartItem.menu_item_id == item_id)
    )
    cart_item = result.scalar_one_or_none()
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(user_id=user_id, menu_item_id=item_id, quantity=quantity)
        session.add(cart_item)
    await session.commit()


async def set_cart_item_quantity(session: AsyncSession, cart_item_id: int, quantity: int) -> None:
    if quantity <= 0:
        cart_item = await session.get(CartItem, cart_item_id)
        if cart_item:
            await session.delete(cart_item)
            await session.commit()
    else:
        await session.execute(update(CartItem).where(CartItem.id == cart_item_id).values(quantity=quantity))
        await session.commit()


async def remove_cart_item(session: AsyncSession, cart_item_id: int) -> None:
    cart_item = await session.get(CartItem, cart_item_id)
    if cart_item:
        await session.delete(cart_item)
        await session.commit()


async def clear_cart(session: AsyncSession, user_id: int) -> None:
    cart_items = await get_cart(session, user_id)
    for ci in cart_items:
        await session.delete(ci)
    await session.commit()


# ---------- Заказы ----------

async def create_order(session: AsyncSession, user_id: int, address: str, phone: str,
                        payment_method: PaymentMethod, comment: str | None,
                        cart_items: list[CartItem]) -> Order:
    total = sum(float(ci.menu_item.price) * ci.quantity for ci in cart_items)
    payment_status = PaymentStatus.NOT_REQUIRED if payment_method == PaymentMethod.CASH else PaymentStatus.PENDING

    order = Order(
        user_id=user_id,
        address=address,
        phone=phone,
        payment_method=payment_method,
        payment_status=payment_status,
        comment=comment,
        total_amount=total,
    )
    session.add(order)
    await session.flush()  # получить order.id до коммита

    for ci in cart_items:
        session.add(OrderItem(
            order_id=order.id,
            menu_item_id=ci.menu_item.id,
            name_snapshot=ci.menu_item.name,
            price_snapshot=ci.menu_item.price,
            quantity=ci.quantity,
        ))

    await session.commit()
    await session.refresh(order)
    return order


async def mark_order_paid(session: AsyncSession, order_id: int) -> None:
    await session.execute(
        update(Order).where(Order.id == order_id).values(payment_status=PaymentStatus.PAID)
    )
    await session.commit()


async def get_order(session: AsyncSession, order_id: int) -> Order | None:
    result = await session.execute(
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.user))
        .where(Order.id == order_id)
    )
    return result.scalar_one_or_none()


async def get_user_orders(session: AsyncSession, user_id: int, limit: int = 10) -> list[Order]:
    result = await session.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_orders_by_status(session: AsyncSession, statuses: list[OrderStatus],
                                limit: int = 50) -> list[Order]:
    result = await session.execute(
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.user))
        .where(Order.status.in_(statuses))
        .order_by(Order.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def update_order_status(session: AsyncSession, order_id: int, status: OrderStatus) -> Order | None:
    await session.execute(update(Order).where(Order.id == order_id).values(status=status))
    await session.commit()
    return await get_order(session, order_id)


# ---------- Статистика для админа ----------

async def get_today_stats(session: AsyncSession):
    from datetime import datetime, time as dtime

    today_start = datetime.combine(datetime.now().date(), dtime.min)
    result = await session.execute(
        select(Order).where(Order.created_at >= today_start, Order.status != OrderStatus.CANCELLED)
    )
    orders = list(result.scalars().all())
    revenue = sum(float(o.total_amount) for o in orders)
    return {"count": len(orders), "revenue": revenue}
