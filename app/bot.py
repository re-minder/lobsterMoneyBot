import asyncio
import logging
from typing import Optional

from telegram import (
    InlineQueryResultCachedVideo,
    InlineQueryResultArticle,
    InputTextMessageContent,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    InlineQueryHandler,
    MessageHandler,
    filters,
)

from .config import load_config
from .db import Database


logger = logging.getLogger(__name__)


class BotApp:
    def __init__(self) -> None:
        self._config = load_config()
        self._db = Database(self._config.db_path)

    async def _ensure_db(self) -> None:
        await self._db.init()
        await self._db.seed_owners(self._config.owner_ids)

    def _is_owner(self, user_id: Optional[int]) -> bool:
        return bool(user_id) and int(user_id) in set(self._config.owner_ids)

    async def start_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user:
            return
        is_owner = self._is_owner(user.id)
        if is_owner:
            await update.effective_message.reply_text(
                "You are an owner. To store a video: 1) Send a video, 2) Reply to it with /remember <phrase>."
            )
        else:
            await update.effective_message.reply_text(
                "Use inline: type @%s <phrase> in any chat to get videos." % (self._config.bot_username or "<your_bot>")
            )

    async def add_owner_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not self._is_owner(user.id):
            return
        if not context.args:
            await update.effective_message.reply_text("Usage: /add_owner <user_id>")
            return
        try:
            new_owner_id = int(context.args[0])
        except ValueError:
            await update.effective_message.reply_text("Invalid user_id")
            return
        await self._db.add_owner(new_owner_id, None)
        await update.effective_message.reply_text(f"Owner {new_owner_id} added.")

    async def status_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not self._is_owner(user.id):
            return
        page_size = 50
        page = 1
        if context.args and len(context.args) >= 1:
            try:
                page = max(1, int(context.args[0]))
            except ValueError:
                page = 1
        total = await self._db.count_mappings()
        if total == 0:
            await update.effective_message.reply_text("No mappings yet.")
            return
        max_page = max(1, (total + page_size - 1) // page_size)
        page = min(page, max_page)
        offset = (page - 1) * page_size
        items = await self._db.list_mappings_paginated(limit=page_size, offset=offset)
        lines = [f"Page {page}/{max_page} — total {total}"]
        for it in items:
            owner = it.get("owner_username") or it.get("owner_user_id")
            lines.append(f"{it['id']}. '{it['phrase']}' → {it['file_id']} (by {owner})")
        lines.append("\nUse /status <page> to navigate.")
        await update.effective_message.reply_text("\n".join(lines))

    async def remember_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not self._is_owner(user.id):
            return
        if not context.args:
            await update.effective_message.reply_text("Usage: reply to a video with /remember <phrase>")
            return
        phrase = " ".join(context.args).strip()
        if not phrase:
            await update.effective_message.reply_text("Provide a non-empty phrase.")
            return
        # Must be a reply to a video message
        if not update.effective_message or not update.effective_message.reply_to_message:
            await update.effective_message.reply_text("Reply to a video with this command.")
            return
        replied = update.effective_message.reply_to_message
        if not replied.video:
            await update.effective_message.reply_text("The replied message does not contain a video.")
            return
        file_id = replied.video.file_id
        await self._db.add_mapping(
            phrase=phrase,
            file_id=file_id,
            owner_user_id=user.id,
            owner_username=user.username,
        )
        await update.effective_message.reply_text(f"Saved phrase '{phrase}'.")

    async def inline_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.inline_query.query if update.inline_query else ""
        query = query.strip()
        if not query:
            return
        items = await self._db.search(query, limit=10)
        results = []
        if not items:
            # Provide a hint result
            results.append(
                InlineQueryResultArticle(
                    id="noop",
                    title="No matches",
                    input_message_content=InputTextMessageContent(
                        f"No results for '{query}'. Try another phrase."
                    ),
                    description="No saved videos match this phrase.",
                )
            )
        else:
            for it in items:
                results.append(
                    InlineQueryResultCachedVideo(
                        id=str(it["id"]),
                        video_file_id=it["file_id"],
                        title=it["phrase"],
                        description=it.get("owner_username") or str(it.get("owner_user_id") or ""),
                    )
                )
        await update.inline_query.answer(results=results, cache_time=0, is_personal=True)

    async def on_error(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.exception("Update caused error: %s", context.error)

    def run(self) -> None:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
        # Ensure DB is ready before starting polling
        asyncio.run(self._ensure_db())

        # Ensure a current event loop exists for ApplicationBuilder on Python 3.8
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        application: Application = (
            ApplicationBuilder()
            .token(self._config.bot_token)
            .build()
        )
        application.add_handler(CommandHandler("start", self.start_cmd))
        application.add_handler(CommandHandler("status", self.status_cmd))
        application.add_handler(CommandHandler("remember", self.remember_cmd))
        application.add_handler(CommandHandler("add_owner", self.add_owner_cmd))
        application.add_handler(InlineQueryHandler(self.inline_query))
        application.add_error_handler(self.on_error)

        logger.info("Bot started")
        application.run_polling(drop_pending_updates=True)


def main() -> None:
    app = BotApp()
    app.run()


if __name__ == "__main__":
    main()


