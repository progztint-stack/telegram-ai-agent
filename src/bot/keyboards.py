"""Telegram keyboards."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("حالة النظام", callback_data="status"),
            InlineKeyboardButton("المهام", callback_data="tasks"),
        ]
    ])
