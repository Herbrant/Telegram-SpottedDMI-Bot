# pylint: disable=unused-argument,redefined-outer-name
"""Tests the bot functionality"""
from datetime import datetime
from typing import Tuple
import pytest
from telegram import Chat, Message, MessageEntity, user
from modules.utils.constants import APPROVED_KB, REJECTED_KB
from modules.data import Config, read_md, DbManager, User, PendingPost, PublishedPost, Report
from modules.handlers.constants import CHAT_PRIVATE_ERROR, AUTOREPLIES
from .telegram_simulator import TelegramSimulator

@pytest.fixture(scope="function")
def local_table(init_local_test_db: DbManager) -> DbManager:
    """Called once per at the beginning of each function.
    Resets the state of the database
    """
    init_local_test_db.query_from_file("data", "db", "meme_db_del.sql")
    init_local_test_db.query_from_file("data", "db", "meme_db_init.sql")
    return init_local_test_db


@pytest.fixture(scope="function")
def telegram(local_table: DbManager) -> TelegramSimulator:
    """Called once per at the beginning of each function.
    Creates a telegram simulator object

    Returns:
        telegram weaver
    """
    return TelegramSimulator()


@pytest.fixture(scope="function")
def pending_post_message(local_table: DbManager, admin_group: Chat) -> Message:
    """Called once per at the beginning of each function.
    Simulates an existing pending post

    Returns:
        pending post message
    """
    PendingPost(1, 0, 0, Config.meme_get('group_id'), datetime.now()).save_post()
    return Message(message_id=0, date=datetime.now(), chat=admin_group)


@pytest.fixture(scope="function")
def published_post_message(telegram: TelegramSimulator, channel: Chat, channel_group: Chat) -> Message:
    """Called once per at the beginning of each function.
    Simulates an existing published post

    Returns:
        published post message
    """
    c_message = Message(message_id=0, date=datetime.now(), chat=channel)
    telegram.add_message(c_message)

    if Config.meme_get('comments'):
        telegram.send_forward_message(forward_message=c_message,
                                      chat=channel_group,
                                      is_automatic_forward=True,
                                      user=user.User(1, first_name="Telegram", is_bot=False))
        assert PublishedPost(channel_id=channel_group, c_message_id=telegram.last_message.message_id)
        return telegram.last_message

    PublishedPost(channel.id, c_message.message_id).save_post()
    return c_message


@pytest.fixture(scope="function")
def report_user_message(local_table: DbManager, admin_group: Chat) -> Message:
    """Called once per at the beginning of each function.
    Simulates an existing user report

    Returns:
        user report message
    """
    Report(1, Config.meme_get('group_id'), 0, target_username='BadUser', date=datetime.now()).save_report()
    return Message(message_id=0, date=datetime.now(), chat=admin_group)


@pytest.fixture(scope="function")
def report_spot_message(local_table: DbManager, admin_group: Chat, channel: Chat) -> Tuple[Message, Message]:
    """Called once per at the beginning of each function.
    Simulates an existing spot report

    Returns:
        spot report in the admin group and post in the channel
    """
    Report(1, Config.meme_get('group_id'), 0, channel_id=Config.meme_get('channel_id'), c_message_id=1,
           date=datetime.now()).save_report()
    group_message = Message(message_id=0, date=datetime.now(), chat=admin_group)
    channel_message = Message(message_id=1, date=datetime.now(), chat=channel)
    return group_message, channel_message


@pytest.fixture(scope="class")
def channel() -> Chat:
    """Called once per at the beginning of each class.
    Returns the channel chat

    Returns:
        channel chat
    """
    group_id = Config.meme_get('channel_id')
    return Chat(id=group_id, type=Chat.CHANNEL)


@pytest.fixture(scope="class")
def admin_group() -> Chat:
    """Called once per at the beginning of each class.
    Returns the admin group chat

    Returns:
        admin group chat
    """
    group_id = Config.meme_get('group_id')
    return Chat(id=group_id, type=Chat.GROUP)


@pytest.fixture(scope="class")
def channel_group() -> Chat:
    """Called once per at the beginning of each class.
    Returns the chat of the public group with the comments

    Returns:
        public group for comments
    """
    channel_group_id = Config.meme_get('channel_group_id')
    return Chat(id=channel_group_id, type=Chat.GROUP)


class TestBot:
    """Tests the bot simulating the telegram API's responses"""

    class TestBotBasicCommand:
        """Tests the bot commands"""

        def test_start_cmd(self, telegram: TelegramSimulator):
            """Tests the /start command.
            The bot sends the start response to the user
            """
            telegram.send_command("/start")
            assert telegram.last_message.text == read_md("start")

        def test_help_user_cmd(self, telegram: TelegramSimulator):
            """Tests the /help command.
            The bot sends the help response to the user
            """
            telegram.send_command("/help")
            assert telegram.last_message.text == read_md("help")

        def test_help_admin_cmd(self, telegram: TelegramSimulator, admin_group: Chat):
            """Tests the /help command.
            The bot sends the help response to the admins
            """
            telegram.send_command("/help", chat=admin_group)
            assert telegram.last_message.text == read_md("instructions")

        def test_rules_cmd(self, telegram: TelegramSimulator):
            """Tests the /rules command.
            The bot sends the rules response to the user
            """
            telegram.send_command("/rules")
            assert telegram.last_message.text == read_md("rules")

    class TestBotAdminCommand:
        """Tests the bot commands reserved for admins"""

        def test_ban_cmd(self, telegram: TelegramSimulator, admin_group: Chat, pending_post_message: Message):
            """Tests the /ban command.
            The bot bans the user associated with the pending post
            """
            telegram.send_message("/ban", chat=admin_group, reply_to_message=pending_post_message)
            assert telegram.last_message.text == "L'utente è stato bannato"
            assert PendingPost.from_group(pending_post_message.message_id, pending_post_message.chat_id) is None
            assert User(1).is_banned

        def test_sban_invalid_cmd(self, telegram: TelegramSimulator, admin_group: Chat):
            """Tests the /sban command.
            The bot warns about invalid command
            """
            telegram.send_command("/sban", chat=admin_group)
            assert telegram.last_message.text == "[uso]: /sban <user_id1> [...user_id2]"

        def test_sban_cmd(self, telegram: TelegramSimulator, admin_group: Chat):
            """Tests the /sban command.
            The bot sbans the users specified user
            """
            User(1).ban()
            telegram.send_command("/sban 1", chat=admin_group)
            assert telegram.last_message.text == "Sban effettuato"
            assert not User(1).is_banned

        def test_reply_invalid_cmd(self, telegram: TelegramSimulator, admin_group: Chat, pending_post_message: Message):
            """Tests the /reply command.
            The bot warns about invalid command
            """
            telegram.send_message("/reply", chat=admin_group, reply_to_message=pending_post_message)
            assert telegram.last_message.text.startswith("La reply è vuota\n")

        def test_reply_post_cmd(self, telegram: TelegramSimulator, admin_group: Chat, pending_post_message: Message):
            """Tests the /reply command.
            The bot sends a message to the user on behalf of the admin
            """
            telegram.send_message("/reply TEST", chat=admin_group, reply_to_message=pending_post_message)
            assert telegram.messages[-2].text.startswith("COMUNICAZIONE DEGLI ADMIN SUL TUO ULTIMO POST:\n")
            assert telegram.messages[-2].text.endswith("TEST")
            assert telegram.last_message.text == "L'utente ha ricevuto il messaggio"

        def test_reply_report_user_cmd(self, telegram: TelegramSimulator, admin_group: Chat, report_user_message: Message):
            """Tests the /reply command.
            The bot sends a message to the user on behalf of the admin
            """
            telegram.send_message("/reply TEST", chat=admin_group, reply_to_message=report_user_message)
            assert telegram.messages[-2].text.startswith("COMUNICAZIONE DEGLI ADMIN SUL TUO ULTIMO REPORT:\n")
            assert telegram.messages[-2].text.endswith("TEST")
            assert telegram.last_message.text == "L'utente ha ricevuto il messaggio"

        def test_reply_report_spot_cmd(self, telegram: TelegramSimulator, admin_group: Chat, report_spot_message: Message):
            """Tests the /reply command.
            The bot sends a message to the user on behalf of the admin
            """
            group_message, _ = report_spot_message
            telegram.send_message("/reply TEST", chat=admin_group, reply_to_message=group_message)
            assert telegram.messages[-2].text.startswith("COMUNICAZIONE DEGLI ADMIN SUL TUO ULTIMO REPORT:\n")
            assert telegram.messages[-2].text.endswith("TEST")
            assert telegram.last_message.text == "L'utente ha ricevuto il messaggio"

        def test_clean_pending(self, telegram: TelegramSimulator, admin_group: Chat):
            """Tests the /clean_pending command.
            The bot cleans the old pending posts, while ignoring the more recent ones
            """
            # An old an a recent pending posts are present
            PendingPost(1, 1, 1, Config.meme_get('group_id'), datetime.fromtimestamp(1)).save_post()
            PendingPost(2, 2, 2, Config.meme_get('group_id'), datetime.now()).save_post()
            telegram.send_command("/clean_pending", chat=admin_group)
            assert telegram.messages[
                -2].text == "Gli admin erano sicuramente molto impegnati e non sono riusciti a valutare lo spot in tempo"
            assert telegram.last_message.text == "Sono stati eliminati 1 messaggi rimasti in sospeso"
            assert PendingPost.from_user(1) is None
            assert PendingPost.from_user(2) is not None

        def test_autoreply_invalid_cmd(self, telegram: TelegramSimulator, admin_group: Chat, pending_post_message: Message):
            """Tests the /autoreply command.
            The bot lists all available autoreplies
            """
            telegram.send_message("/autoreply", chat=admin_group, reply_to_message=pending_post_message)
            assert telegram.last_message.text == read_md("autoreply_list")

        def test_autoreply_unknown_cmd(self, telegram: TelegramSimulator, admin_group: Chat, pending_post_message: Message):
            """Tests the /autoreply command.
            The bot lists all available autoreplies
            """
            telegram.send_message("/autoreply unknown", chat=admin_group, reply_to_message=pending_post_message)
            assert telegram.last_message.text == read_md("autoreply_list")

        def test_autoreply_list_cmd(self, telegram: TelegramSimulator, admin_group: Chat, pending_post_message: Message):
            """Tests the /reply command.
            The bot sends an automatic reply to the user
            """
            # remove the "list" special autoreply
            telegram.send_message("/autoreply list", chat=admin_group, reply_to_message=pending_post_message)
            assert telegram.last_message.text == read_md("autoreply_list")

        def test_autoreply_cmd(self, telegram: TelegramSimulator, admin_group: Chat, pending_post_message: Message):
            """Tests the /reply command.
            The bot sends an automatic reply to the user
            """
            # remove the "list" special autoreply
            filtered_autoreplies = ((autoreply, file) for (autoreply, file) in AUTOREPLIES.items() if autoreply != "lista")
            for (autoreply, file) in filtered_autoreplies:
                telegram.send_message(f"/autoreply {autoreply}", chat=admin_group, reply_to_message=pending_post_message)
                assert telegram.messages[-2].text.startswith("COMUNICAZIONE DEGLI ADMIN SUL TUO ULTIMO POST:\n")
                assert telegram.messages[-2].text.endswith(read_md(file))
                assert telegram.last_message.text == "L'utente ha ricevuto il messaggio"

    class TestBotSpotConversation:
        """Tests the spot conversation"""

        def test_spot_no_private_cmd(self, telegram: TelegramSimulator, channel_group: Chat):
            """Tests the /spot command.
            Spot is not allowed in groups
            """
            telegram.send_command("/spot", chat=channel_group)
            assert telegram.last_message.text == CHAT_PRIVATE_ERROR

        def test_spot_banned_cmd(self, telegram: TelegramSimulator):
            """Tests the /spot command.
            Spot is not allowed for banned users
            """
            User(1).ban()  # by default the user used by the telegram simulator has id 1
            telegram.send_command("/spot")
            assert telegram.last_message.text == "Sei stato bannato 😅"

        def test_spot_pending_cmd(self, telegram: TelegramSimulator):
            """Tests the /spot command.
            Spot is not allowed for users with a pending post
            """
            PendingPost(user_id=1, u_message_id=1, g_message_id=1, group_id=1, date=datetime.now()).save_post()
            telegram.send_command("/spot")
            assert telegram.last_message.text == "Hai già un post in approvazione 🧐"

        def test_spot_cancel_cmd(self, telegram: TelegramSimulator):
            """Tests the /spot command.
            Cancel spot conversation
            """
            telegram.send_command("/spot")
            assert telegram.last_message.text == "Invia il post che vuoi pubblicare"

            telegram.send_command("/cancel")
            assert telegram.last_message.text == read_md("spot_cancel")

            telegram.send_command("/spot")
            assert telegram.last_message.text == "Invia il post che vuoi pubblicare"

        def test_spot_no_cmd(self, telegram: TelegramSimulator):
            """Tests the /spot command.
            Complete with no the spot conversation
            """
            telegram.send_command("/spot")
            assert telegram.last_message.text == "Invia il post che vuoi pubblicare"

            telegram.send_message("Test spot")
            assert telegram.last_message.text == "Sei sicuro di voler pubblicare questo post?"
            assert telegram.last_message.reply_to_message is not None

            telegram.send_callback_query(text="No")
            assert telegram.last_message.text in read_md("no_strings").split("\n")

            telegram.send_command("/spot")
            assert telegram.last_message.text == "Invia il post che vuoi pubblicare"

        def test_spot_si_cmd(self, telegram: TelegramSimulator):
            """Tests the /spot command.
            Complete with yes the spot conversation
            """
            telegram.send_command("/spot")
            assert telegram.last_message.text == "Invia il post che vuoi pubblicare"

            telegram.send_message("Test spot")
            assert telegram.last_message.text == "Sei sicuro di voler pubblicare questo post?"
            assert telegram.last_message.reply_to_message is not None

            telegram.send_callback_query(text="Si")
            assert telegram.last_message.text == "Il tuo post è in fase di valutazione\n"\
                f"Una volta pubblicato, lo potrai trovare su {Config.meme_get('channel_tag')}"

            telegram.send_command("/spot")
            assert telegram.last_message.text == "Hai già un post in approvazione 🧐"

            PendingPost.from_user(1).delete_post()
            telegram.send_command("/spot")
            assert telegram.last_message.text == "Invia il post che vuoi pubblicare"

        def test_spot_link_cmd(self, telegram: TelegramSimulator):
            """Tests the /spot command.
            Send spot with a link
            """
            telegram.send_command("/spot")
            assert telegram.last_message.text == "Invia il post che vuoi pubblicare"

            telegram.send_message("Hai vinto un iPad 🎉",
                                  entities=[
                                      MessageEntity(type=MessageEntity.URL,
                                                    offset=0,
                                                    length=19,
                                                    url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
                                  ])

            assert telegram.last_message.text == "Il post contiene link, vuoi pubblicare con l'anteprima?"

        def test_spot_link_with_preview_cmd(self, telegram: TelegramSimulator):
            """Tests the /spot command.
            Send spot with a link with preview and complete the conversation
            """
            self.test_spot_link_cmd(telegram)
            telegram.send_callback_query(text="Si")

            assert telegram.last_message.text == "Sei sicuro di voler pubblicare questo post?"

        def test_spot_link_without_preview_cmd(self, telegram: TelegramSimulator):
            """Tests the /spot command.
            Send spot with a link with preview and complete the conversation
            """
            self.test_spot_link_cmd(telegram)
            telegram.send_callback_query(text="No")

            assert telegram.last_message.text == "Sei sicuro di voler pubblicare questo post?"

    class TestBotSettings:
        """Tests the settings commands"""

        def test_settings_cmd(self, telegram: TelegramSimulator):
            """Tests the /settings command.
            The bot sends the settings response to the user
            """
            telegram.send_command("/settings")
            assert telegram.last_message.text == "***Come vuoi che sia il tuo post:***"

        def test_settings_anonym_from_anonym_cmd(self, telegram: TelegramSimulator):
            """Tests the /settings command.
            The user becomes anonym already being anonym
            """
            telegram.send_command("/settings")
            assert telegram.last_message.text == "***Come vuoi che sia il tuo post:***"

            telegram.send_callback_query(text=" Anonimo ")
            assert telegram.last_message.text == "Sei già anonimo"

            assert not User(1).is_credited

        def test_settings_anonym_from_credited_cmd(self, telegram: TelegramSimulator):
            """Tests the /settings command.
            The user becomes anonym from being credited
            """
            User(1).become_credited()
            telegram.send_command("/settings")
            assert telegram.last_message.text == "***Come vuoi che sia il tuo post:***"

            telegram.send_callback_query(text=" Anonimo ")
            assert telegram.last_message.text == "La tua preferenza è stata aggiornata\n"\
                                                    "Ora i tuoi post saranno anonimi"
            assert not User(1).is_credited

        def test_settings_credited_from_anonym_cmd(self, telegram: TelegramSimulator):
            """Tests the /settings command.
            The user becomes credited from being anonym
            """
            telegram.send_command("/settings")
            assert telegram.last_message.text == "***Come vuoi che sia il tuo post:***"

            telegram.send_callback_query(text=" Con credit ")
            assert telegram.last_message.text == "La tua preferenza è stata aggiornata\n"\
                                                    f"I tuoi post avranno come credit @{telegram.user.username}"

            assert User(1).is_credited

        def test_settings_credited_from_credited_cmd(self, telegram: TelegramSimulator):
            """Tests the /settings command.
            The user becomes credited already being credited
            """
            User(1).become_credited()
            telegram.send_command("/settings")
            assert telegram.last_message.text == "***Come vuoi che sia il tuo post:***"

            telegram.send_callback_query(text=" Con credit ")
            assert telegram.last_message.text == "Sei già creditato nei post\n"\
                                                    f"I tuoi post avranno come credit @{telegram.user.username}"

            assert User(1).is_credited

    class TestReportUser:
        """Tests the report user commands"""

        def test_report_user_invalid_username_cmd(self, telegram: TelegramSimulator):
            """Tests the /report user command.
            The username submitted is not a valid Telegram username
            """
            telegram.send_command("/report")
            assert telegram.last_message.text == "Invia l'username di chi vuoi segnalare. Es. @massimobene"

            telegram.send_message("massimobene")
            assert telegram.last_message.text.startswith("Questo tipo di messaggio non è supportato\n")

            telegram.send_message("@massimo bene")
            assert telegram.last_message.text.startswith("Questo tipo di messaggio non è supportato\n")

        def test_report_user_cmd(self, telegram: TelegramSimulator):
            """Tests the /report user command.
            The bot sends the report from the user to the admins
            """
            telegram.send_command("/report")
            assert telegram.last_message.text == "Invia l'username di chi vuoi segnalare. Es. @massimobene"

            telegram.send_message("@massimobene")
            assert telegram.last_message.text.startswith("Scrivi il motivo della tua segnalazione.\n")

            telegram.send_message("Motivo segnalazione")

            assert telegram.messages[-2].text.startswith("🚨🚨 SEGNALAZIONE 🚨🚨\n\n")
            assert telegram.last_message.text == "Gli admins verificheranno quanto accaduto. Grazie per la collaborazione!"
            assert Report.get_last_user_report(telegram.user.id) is not None

        def test_report_user_cooldown_cmd(self, telegram: TelegramSimulator):
            """Tests the /report user command's cooldown timer.
            The user cannot report again for the amount of time established in the settings
            """
            telegram.send_command("/report")
            assert telegram.last_message.text == "Invia l'username di chi vuoi segnalare. Es. @massimobene"

            telegram.send_message("@massimobene")
            assert telegram.last_message.text.startswith("Scrivi il motivo della tua segnalazione.\n")

            telegram.send_message("Motivo segnalazione")

            assert telegram.messages[-2].text.startswith("🚨🚨 SEGNALAZIONE 🚨🚨\n\n")
            assert telegram.last_message.text == "Gli admins verificheranno quanto accaduto. Grazie per la collaborazione!"
            assert Report.get_last_user_report(telegram.user.id) is not None

            telegram.send_command("/report")
            assert telegram.last_message.text == f"Aspetta {Config.meme_get('report_wait_mins') - 1} minuti"

    class TestReportSpot:
        """Tests the report spot commands"""

        def test_report_post_query(self, telegram: TelegramSimulator, published_post_message: Message):
            """Tests the /report user query.
            The user successfully reports a post already published in the channel
            """
            telegram.send_callback_query(data="meme_report_spot,", message=published_post_message)
            assert telegram.last_message.text == "Scrivi il motivo della segnalazione del post, altrimenti digita /cancel"

            telegram.send_message("Motivo segnalazione")
            assert telegram.messages[-2].text.startswith("🚨🚨 SEGNALAZIONE 🚨🚨\n\n")
            assert telegram.last_message.text == "Gli admins verificheranno quanto accaduto. Grazie per la collaborazione!"
            assert Report.get_post_report(telegram.user.id, published_post_message.chat_id,
                                          published_post_message.reply_to_message.message_id) is not None

        def test_report_post_again_query(self, telegram: TelegramSimulator, published_post_message: Message):
            """Tests the /report user query.
            The user cannot report again a post already published in the channel
            """
            telegram.send_callback_query(data="meme_report_spot,", message=published_post_message)
            assert telegram.last_message.text == "Scrivi il motivo della segnalazione del post, altrimenti digita /cancel"

            telegram.send_message("Motivo segnalazione")
            assert telegram.messages[-2].text.startswith("🚨🚨 SEGNALAZIONE 🚨🚨\n\n")
            assert telegram.last_message.text == "Gli admins verificheranno quanto accaduto. Grazie per la collaborazione!"
            assert Report.get_post_report(telegram.user.id, published_post_message.chat_id,
                                          published_post_message.reply_to_message.message_id) is not None

            telegram.send_callback_query(data="meme_report_spot,", message=published_post_message)
            # The next message is the same as the last, because if the user try to report again
            # the query will be answered with a warning but no new messages will be sent by the bot
            assert telegram.last_message.text == "Gli admins verificheranno quanto accaduto. Grazie per la collaborazione!"

    class TestSpotLinkPreview:
        """Test the spot link preview"""

        def test_spot_link(self, telegram: TelegramSimulator):
            """Tests the /spot command.
            Send spot with a link
            """
            telegram.send_command("/spot")
            assert telegram.last_message.text == "Invia il post che vuoi pubblicare"

            telegram.send_message("Hai vinto un iPad 🎉",
                                  entities=[
                                      MessageEntity(type=MessageEntity.URL,
                                                    offset=0,
                                                    length=19,
                                                    url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
                                  ])

            assert telegram.last_message.text == "Il post contiene link, vuoi pubblicare con l'anteprima?"
            assert telegram.last_message.reply_to_message is not None

        def test_spot_link_with_preview(self, telegram: TelegramSimulator):
            """Tests the /spot command.
            Complete with yes the spot with link preview conversation
            """
            self.test_spot_link(telegram)

            telegram.send_callback_query(text="Si")
            assert telegram.last_message.text == "Sei sicuro di voler pubblicare questo post?"

            # The last edited message will not have the reply_to_message attribute (because of bot APIs)
            # So instead we use the original message (the one that was sent before the callback query)
            # and specify the data of the callback query manually
            telegram.send_callback_query(data="meme_confirm,submit", message=telegram.messages[-2])
            g_message = telegram.messages[-2]
            types = [entity.type for entity in g_message.entities]
            assert MessageEntity.URL in types

        def test_spot_link_without_preview(self, telegram: TelegramSimulator):
            """Tests the /spot command.
            Complete with no the spot without link preview conversation
            """
            self.test_spot_link(telegram)

            telegram.send_callback_query(text="No")
            assert telegram.last_message.text == "Sei sicuro di voler pubblicare questo post?"

            telegram.send_callback_query(data="meme_confirm,submit", message=telegram.messages[-2])
            g_message = telegram.messages[-2]
            types = [entity.type for entity in g_message.entities]
            assert MessageEntity.URL in types
            # NOTE: There is no way to check if message has preview

    class TestPublishSpot:
        """Tests the complete publishing spot pipeline"""

        def test_spot_pipeline(self, telegram: TelegramSimulator, admin_group: Chat, channel: Chat, channel_group: Chat):
            """Tests the /spot command.
            Complete with yes the spot conversation
            """
            telegram.send_command("/spot")
            assert telegram.last_message.text == "Invia il post che vuoi pubblicare"

            telegram.send_message("Test spot")
            assert telegram.last_message.text == "Sei sicuro di voler pubblicare questo post?"
            assert telegram.last_message.reply_to_message is not None

            telegram.send_callback_query(text="Si")
            g_message = telegram.messages[-2]
            assert g_message.text == "Test spot"
            assert telegram.last_message.text == "Il tuo post è in fase di valutazione\n"\
                f"Una volta pubblicato, lo potrai trovare su {Config.meme_get('channel_tag')}"
            assert PendingPost.from_group(g_message_id=g_message.message_id, group_id=admin_group.id) is not None

            telegram.send_callback_query(text="🟢 0", message=g_message)
            telegram.send_callback_query(text="🟢 1", message=g_message, user=user.User(2, first_name="Test2", is_bot=False))

            assert telegram.messages[-3].text == "Test spot"
            assert telegram.messages[-2].text.startswith("Il tuo ultimo post è stato pubblicato")
            assert telegram.last_message.reply_markup.inline_keyboard[1][0].text == APPROVED_KB

            assert PendingPost.from_group(g_message_id=g_message.message_id, group_id=admin_group.id) is None

            telegram.send_forward_message(forward_message=telegram.messages[-3],
                                          chat=channel_group,
                                          is_automatic_forward=True,
                                          user=user.User(1, first_name="Telegram", is_bot=False))
            assert telegram.last_message.text.startswith("by: ")
            assert PublishedPost(channel_id=channel.id, c_message_id=telegram.last_message.message_id)

    class TestRejectSpot:
        """Tests the complete publishing spot pipeline"""

        @pytest.fixture(autouse=True)
        def test_spot_send(self, telegram: TelegramSimulator, admin_group: Chat):
            """Tests the /spot command.
            Complete with yes the spot conversation
            """
            telegram.send_command("/spot")
            telegram.send_message("Test spot")
            telegram.send_callback_query(text="Si")

        def test_reject_spot(self, telegram: TelegramSimulator, admin_group: Chat):
            """
            Complete with no the spot conversation
            """
            g_message = telegram.messages[-2]
            telegram.send_callback_query(text="🔴 0", message=g_message)
            telegram.send_callback_query(text="🔴 1", message=g_message, user=user.User(2, first_name="Test2", is_bot=False))
            assert telegram.messages[-4].text == "Test spot"
            assert telegram.messages[-2].text.startswith("Il tuo ultimo post è stato rifiutato")
            assert telegram.last_message.reply_markup.inline_keyboard[1][0].text == REJECTED_KB
            assert PendingPost.from_group(g_message_id=g_message.message_id, group_id=admin_group.id) is None

        def test_reject_after_autoreply_spot(self, telegram: TelegramSimulator, admin_group: Chat):
            """
            Test the reject spot after the autoreply
            """
            if not Config.settings_get("meme", "reject_after_autoreply"):
                pytest.skip("Reject after autoreply is disabled")

            g_message = telegram.messages[-2]
            telegram.send_callback_query(text="⏹ Stop", message=g_message)
            autoreplies = Config.autoreplies_get('autoreplies')
            first_autoreply_key = list(autoreplies.keys())[0]
            telegram.send_callback_query(text=first_autoreply_key,
                                            message=g_message,
                                            data=f"meme_autoreply,{first_autoreply_key}")
            assert telegram.messages[-3].text == autoreplies[first_autoreply_key]
            assert telegram.messages[-2].text.startswith("Il tuo ultimo post è stato rifiutato")
            assert telegram.last_message.reply_markup.inline_keyboard[-1][0].text == f"{REJECTED_KB} [{first_autoreply_key}]"


    class TestStoppedSpot:
        """Tests the stopped spot and its navigation for autoreplies"""

        @pytest.fixture(autouse=True)
        def test_spot_send(self, telegram: TelegramSimulator, admin_group: Chat):
            """Tests the /spot command.
            Complete with yes the spot conversation
            """
            telegram.send_command("/spot")
            telegram.send_message("Test spot")
            telegram.send_callback_query(text="Si")
            g_message = telegram.messages[-2]
            telegram.send_callback_query(text="⏹ Stop", message=g_message)

        @pytest.mark.parametrize("autoreply_key", list(Config.autoreplies_get('autoreplies').keys()))
        def test_stop_spot(self, telegram: TelegramSimulator, admin_group: Chat, autoreply_key: str):
            """
            Test autoreplies and navigation on the stopped spot
            """
            g_message = telegram.messages[-3]
            autoreply_message = Config.autoreplies_get('autoreplies')[autoreply_key]

            # find if the autoreply is in the keyboard
            autoreply_found = False
            next_button = telegram.find_button_on_keyboard("⏭ Next", telegram.last_message)

            while next_button:
                if telegram.find_button_on_keyboard(autoreply_key, telegram.last_message):
                    autoreply_found = True
                    break
                next_button = telegram.find_button_on_keyboard("⏭ Next", telegram.last_message)

                if next_button:
                    telegram.send_callback_query(text="⏭ Next", message=g_message, data=next_button.callback_data)

            assert autoreply_found is True

            telegram.send_callback_query(text=autoreply_key,
                                         data=f"meme_autoreply,{autoreply_key}",
                                         message=g_message)

            if Config.settings_get("meme", "reject_after_autoreply"):
                assert telegram.messages[-3].text == autoreply_message
                assert telegram.messages[-2].text.startswith("Il tuo ultimo post è stato rifiutato")
                return

            assert telegram.last_message.text == autoreply_message


    class TestComments:
        """Tests the comments feature in the channel group"""

        def test_non_anonymous_comment_msg(self, telegram: TelegramSimulator, published_post_message: Message,
                                           channel_group: Chat):
            """Tests a public comment.
            The bot should not react to the message if the user is not anonymous
            """
            public_comment = telegram.send_message("Public comment",
                                                   chat=channel_group,
                                                   reply_to_message=published_post_message.reply_to_message,
                                                   user=user.User(10, first_name="user", is_bot=False))

            assert telegram.get_message_with_id(public_comment.message_id) is not None
            assert telegram.last_message.text == "Public comment"
            assert telegram.last_message.from_user.is_bot is False

        def test_anonymous_comment_msg(self, telegram: TelegramSimulator, published_post_message: Message, channel: Chat,
                                       channel_group: Chat):
            """Tests the replacement of an anonymous comment.
            Copies the message and deletes the original
            """
            anonymous_comment = telegram.send_message("Anonymous comment",
                                                      chat=channel_group,
                                                      reply_to_message=published_post_message.reply_to_message,
                                                      user=user.User(10, first_name="user", is_bot=False),
                                                      sender_chat=channel)

            assert telegram.get_message_with_id(anonymous_comment.message_id) is None  # the anonymous comment is deleted
            assert telegram.last_message.text == "Anonymous comment"
            assert telegram.last_message.from_user.is_bot is True
