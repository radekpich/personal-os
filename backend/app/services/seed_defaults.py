from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.context import Context
from app.models.user import User

DEFAULT_CATEGORIES: list[tuple[str, str, str]] = [
    ("KEXO", "#0EA5E9", "briefcase"),
    ("Ranč", "#8B5E3C", "barn"),
    ("Stavba", "#F59E0B", "home"),
    ("Hospodářství", "#22C55E", "tractor"),
    ("Rodina", "#EC4899", "heart"),
    ("Kondice", "#6366F1", "activity"),
]

DEFAULT_CONTEXTS: list[tuple[str, str, str]] = [
    ("Ranč", "#8B5E3C", "barn"),
    ("Staré Buky", "#F59E0B", "home"),
    ("Kancelář", "#0EA5E9", "building"),
    ("Počítač", "#6366F1", "monitor"),
    ("Telefon", "#14B8A6", "phone"),
    ("Město", "#64748B", "map"),
    ("Doma", "#EC4899", "house"),
]

CONTEXT_RENAMES = {
    "@ranč": "Ranč",
    "@Staré Buky": "Staré Buky",
    "@počítač": "Počítač",
    "@telefon": "Telefon",
    "@město": "Město",
}
CATEGORY_RENAMES = {"Ranč na Valech": "Ranč"}


@dataclass(frozen=True)
class SeedDefaultsResult:
    users_seen: int
    categories_created: int
    categories_updated: int
    contexts_created: int
    contexts_updated: int


async def seed_defaults(db: AsyncSession) -> SeedDefaultsResult:
    users = list((await db.execute(select(User))).scalars().all())
    categories_created = categories_updated = contexts_created = contexts_updated = 0

    for user in users:
        categories = list(
            (
                await db.execute(
                    select(Category).where(
                        Category.owner_id == user.id, Category.deleted_at.is_(None)
                    )
                )
            )
            .scalars()
            .all()
        )
        categories_by_name = {category.name.casefold(): category for category in categories}
        now = datetime.now(UTC)
        for old, new in CATEGORY_RENAMES.items():
            category_row = categories_by_name.get(old.casefold())
            existing_new = categories_by_name.get(new.casefold())
            if category_row and existing_new is None:
                category_row.name = new
                categories_by_name[new.casefold()] = category_row
                categories_updated += 1
            elif category_row and existing_new is not None:
                category_row.is_archived = True
                category_row.deleted_at = now
                categories_updated += 1
        for position, (name, color, icon) in enumerate(DEFAULT_CATEGORIES):
            category_row = categories_by_name.get(name.casefold())
            if category_row is None:
                db.add(
                    Category(owner_id=user.id, name=name, color=color, icon=icon, position=position)
                )
                categories_created += 1
            else:
                changed = False
                if not category_row.color:
                    category_row.color = color
                    changed = True
                if not category_row.icon:
                    category_row.icon = icon
                    changed = True
                if category_row.is_archived:
                    category_row.is_archived = False
                    changed = True
                if changed:
                    categories_updated += 1

        contexts = list(
            (
                await db.execute(
                    select(Context).where(Context.owner_id == user.id, Context.deleted_at.is_(None))
                )
            )
            .scalars()
            .all()
        )
        contexts_by_name = {context.name.casefold(): context for context in contexts}
        for old, new in CONTEXT_RENAMES.items():
            context_row = contexts_by_name.get(old.casefold())
            existing_context = contexts_by_name.get(new.casefold())
            if context_row and existing_context is None:
                context_row.name = new
                contexts_by_name[new.casefold()] = context_row
                contexts_updated += 1
            elif context_row and existing_context is not None:
                context_row.is_archived = True
                context_row.deleted_at = now
                contexts_updated += 1
        for position, (name, color, icon) in enumerate(DEFAULT_CONTEXTS):
            context_row = contexts_by_name.get(name.casefold())
            if context_row is None:
                db.add(
                    Context(owner_id=user.id, name=name, color=color, icon=icon, position=position)
                )
                contexts_created += 1
            else:
                changed = False
                if not context_row.color:
                    context_row.color = color
                    changed = True
                if not context_row.icon:
                    context_row.icon = icon
                    changed = True
                if context_row.is_archived:
                    context_row.is_archived = False
                    changed = True
                if changed:
                    contexts_updated += 1

    await db.commit()
    return SeedDefaultsResult(
        users_seen=len(users),
        categories_created=categories_created,
        categories_updated=categories_updated,
        contexts_created=contexts_created,
        contexts_updated=contexts_updated,
    )
