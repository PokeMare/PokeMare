import time

import disnake
from datetime import datetime
import uuid
import math
import json


class Mail:
    def __init__(
        self,
        from_id: int = 0,
        from_author: str = "",
        to_id: int = 0,
        subject: str = "",
        message: str = "",
        mail_type: str = "standard",
        item=None,
        pokemon=None,
    ):
        self.unique_id = uuid.uuid4()
        self.from_id = from_id
        self.from_author = from_author
        self.to_id = to_id
        self.subject = subject
        self.message = message
        self.mail_type = mail_type
        self.item = item
        self.pokemon = pokemon
        self.timestamp = datetime.today()
        self.read = False

    def __str__(self):
        return self.to_string()

    def has_attachments(self):
        if self.item or self.pokemon:
            return True
        return False

    def receive_all_attachments(self):
        self.receive_item()
        self.receive_pokemon()

    def receive_item(self):
        if self.item:
            # TODO: Give item to user
            pass
        self.item = None

    def receive_pokemon(self):
        if self.pokemon:
            # TODO: Give Pokemon to user
            pass
        self.pokemon = None

    def add_item(self, item):
        self.item = item

    def add_pokemon(self, pokemon):
        self.pokemon = pokemon

    def to_string(self):
        # TODO: item.to_string()
        #item_json = self.item.to_string()
        item_json = str(self.item)

        #TODO: pokemon.to_string()
        #pokemon_json = self.pokemon.to_string()
        pokemon_json = str(self.pokemon)

        json_dict = {
            'unique_id': self.unique_id.hex,
            "from_id": self.from_id,
            "from_author": self.from_author,
            "to_id": self.to_id,
            "subject": self.subject,
            "message": self.message,
            "mail_type": self.mail_type,
            "item": item_json,
            "pokemon": pokemon_json,
            "timestamp": self.timestamp.isoformat(),
            "read": self.read
        }
        mail_string = json.dumps(json_dict)
        return mail_string

    def from_string(self, mail_string):
        mail_json = json.loads(mail_string)
        self.unique_id = uuid.UUID(mail_json['unique_id'])
        self.from_id = int(mail_json['from_id'])
        self.from_author = mail_json['from_author']
        self.to_id = int(mail_json['to_id'])
        self.subject = mail_json['subject']
        self.message = mail_json['message']
        self.mail_type = mail_json['mail_type']
        # TODO: self.item = Item().from_string(mail_json['item'])
        self.item = None
        # TODO: self.pokemon = Pokemon().from_string(mail_json['pokemon'])
        self.pokemon = None
        self.timestamp = datetime.fromisoformat(mail_json['timestamp'])
        self.read = bool(mail_json['read'])


class MailBox:
    def __init__(self, user_identifier: int = 0):
        self.mail_dict = {}
        self.user_identifier = user_identifier
        self.unread = 0
        self.items_waiting = 0
        self.pokemon_waiting = 0

    def __str__(self):
        return self.to_string()

    def add_mail(self, mail: Mail):
        self.mail_dict[mail.unique_id] = mail

    def delete_mail(self, unique_id):
        if unique_id in self.mail_dict.keys():
            del self.mail_dict[unique_id]

    def mark_mail_as_read(self, mail):
        if mail.unique_id in self.mail_dict.keys():
            self.mail_dict[mail.unique_id].read = True

    def claim_mail_attachments(self, mail):
        if mail.unique_id in self.mail_dict.keys():
            self.mail_dict[mail.unique_id].receive_all_attachments()

    def sort_mailbox_by_date(self):
        mail_list = list(self.mail_dict.values())
        mail_list.sort(key=lambda m: m.timestamp, reverse=True)
        mail_list.sort(key=lambda m: m.read)
        return mail_list

    def update_fields(self):
        self.unread = 0
        self.items_waiting = 0
        self.pokemon_waiting = 0
        for mail in list(self.mail_dict.values()):
            if not mail.read:
                self.unread += 1
            if mail.item:
                self.items_waiting += 1
            if mail.pokemon:
                self.pokemon_waiting += 1

    def to_string(self):
        mail_list = []
        for mail in list(self.mail_dict.values()):
            mail_list.append(mail.to_string())
        json_dict = {
            "mail_dict": mail_list,
            "user_identifier": self.user_identifier
        }
        mailbox_string = json.dumps(json_dict)
        return mailbox_string

    def from_string(self, mailbox_string):
        mailbox_json = json.loads(mailbox_string)
        for mail_string in mailbox_json['mail_dict']:
            mail = Mail()
            mail.from_string(mail_string)
            self.mail_dict[mail.unique_id] = mail
        self.user_identifier = int(mailbox_json['user_identifier'])
        self.update_fields()


class MailBoxUIManager:
    def __init__(self, bot, user, mailbox):
        self.bot = bot
        self.user = user
        self.inbox_offset = 0
        self.mail = None
        self.started = False

    async def start(self, interaction):
        await self.launch_home(interaction)

    async def next(self, from_ui, next_ui, interaction):
        if next_ui == "home":
            await self.launch_home(interaction)
        elif next_ui == "inbox":
            if from_ui == "home":
                self.inbox_offset = 0
            await self.launch_inbox(interaction)
        elif next_ui == "read mail":
            await self.launch_read_message(interaction)

    async def launch_home(self, interaction):
        await self.user.refresh_data()
        await self.user.update_mailbox_fields()
        embed = MailHomeEmbed(interaction.author, self.user)
        view = MailHomeView(self.bot, interaction.author, self.user)
        if self.started:
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            self.started = True
            await interaction.send(embed=embed, view=view, ephemeral=True)
        await view.wait()
        await self.next("home", view.next, view.interaction)

    async def launch_inbox(self, interaction):
        await self.user.refresh_data()
        await self.user.update_mailbox_fields()
        embed = InboxEmbed(interaction.author, self.user, self.inbox_offset)
        view = InboxView(self.bot, interaction.author, self.user, self.inbox_offset)
        await interaction.response.edit_message(embed=embed, view=view)
        await view.wait()
        self.inbox_offset = view.page_offset
        self.mail = view.mail
        await self.next("inbox", view.next, view.interaction)

    async def launch_read_message(self, interaction):
        await self.user.refresh_data()
        await self.user.mark_mail_as_read(self.mail)
        embed = MailReadEmbed(interaction.author, self.user, self.mail)
        view = MailReadView(self.bot, interaction.author, self.user, self.mail, self.inbox_offset)
        await interaction.response.edit_message(embed=embed, view=view)
        await view.wait()
        self.inbox_offset = view.page_offset
        await self.next("read mail", view.next, view.interaction)


class MailHomeEmbed(disnake.embeds.Embed):
    def __init__(self, inter_author, user):
        super().__init__(
            title="Welcome to your PokéMare Mailbox!",
            description=":mailbox_with_mail:・Unread Messages: "
            + str(user.mailbox.unread)
            + "\n"
            "<:potion:941956192010371073>・Unclaimed Items: "
            + str(user.mailbox.items_waiting)
            + "\n"
            "<:POKEMON:942110736577077268>・Unclaimed Pokemon: "
            + str(user.mailbox.pokemon_waiting)
            + "\n\n\n"
            ":mailbox:・Click 'Inbox' below to view your inbox.\n"
            ":incoming_envelope:・Click 'Send' below to send a new mail.\n",
        )
        self.inter_author = inter_author
        self.init_footer()
        self.init_thumbnail()
        self.color = disnake.Color.blue()

    def init_footer(self):
        self.set_footer(
            text=f"MailBox for {self.inter_author}",
            icon_url=self.inter_author.display_avatar,
        )

    def init_thumbnail(self):
        self.set_thumbnail(url="https://i.imgur.com/BR7T4zp.png")


class InboxEmbed(disnake.embeds.Embed):
    def __init__(self, inter_author, user, page_offset=0):
        super().__init__(
            title="PokéMare Inbox (pg." + str(page_offset + 1) + ")",
            description=(
                ":mailbox_with_mail:・Unread Messages: "
                + str(user.mailbox.unread)
                + "\n-------------------------------------"
            ),
        )
        self.inter_author = inter_author
        self.init_footer()
        self.init_thumbnail()
        self.page_offset = page_offset
        self.mail_list = user.mailbox.sort_mailbox_by_date()
        self.color = disnake.Color.blue()
        self.init_fields()

    def init_fields(self):
        emoji_list = [":one:", ":two:", ":three:", ":four:", ":five:"]
        for x in range(5):
            index = x + self.page_offset * 5
            if index < len(self.mail_list):
                mail = self.mail_list[index]
                subject_unread = ""
                if not mail.read:
                    subject_unread = " ✉️"
                value_str = (
                    "*From*: "
                    + str(mail.from_author)
                    + "\n*Time*: "
                    + mail.timestamp.strftime("%m/%d/%Y, %I:%M:%S %p")
                    + "\n"
                )
                value_str_append = ""
                if mail.has_attachments():
                    value_str_append = "Att: "
                    if mail.pokemon:
                        value_str_append += "<:POKEMON:942110736577077268>"
                    if mail.item:
                        value_str_append += "<:potion:941956192010371073>"
                    value_str_append += "\n"
                value_str = (
                    value_str
                    + value_str_append
                    + "\n__Message preview:__\n"
                    + mail.message[:30]
                    + "..."
                )
                value_str += "\n\n-------------------------------------"
                self.add_field(
                    name=emoji_list[x] + " SUBJECT: " + mail.subject + subject_unread,
                    value=value_str,
                    inline=False,
                )
            else:
                self.add_field(
                    name=emoji_list[x]
                    + " - Empty mail slot"
                    + "\n\n----------------------",
                    value="\u200b",
                    inline=False,
                )

    def init_footer(self):
        self.set_footer(
            text=f"MailBox for {self.inter_author}",
            icon_url=self.inter_author.display_avatar,
        )

    def init_thumbnail(self):
        self.set_thumbnail(url="https://i.imgur.com/BR7T4zp.png")


class MailReadEmbed(disnake.embeds.Embed):
    def __init__(self, inter_author, user, mail):
        # TODO: Make attachments more specific once we have items and Pokemon implemented
        attachment_str = ""
        if mail.has_attachments():
            attachment_str = "*ATTACHMENTS*: "
            if mail.pokemon:
                attachment_str += "<:POKEMON:942110736577077268>"
            if mail.item:
                attachment_str += "<:potion:941956192010371073>"
            attachment_str += "\n"
        description_str = (
            "*FROM:* "
            + str(mail.from_author)
            + "\n"
            + "*TIME*: "
            + mail.timestamp.strftime("%m/%d/%Y, %I:%M:%S %p" + "\n" + attachment_str)
        )
        super().__init__(title="SUBJECT: " + mail.subject, description=description_str)
        self.inter_author = inter_author
        self.init_footer()
        self.init_thumbnail()
        self.init_fields(mail)
        self.color = disnake.Color.blue()

    def init_footer(self):
        self.set_footer(
            text=f"MailBox for {self.inter_author}",
            icon_url=self.inter_author.display_avatar,
        )

    def init_thumbnail(self):
        # TODO: Make thumbnail the type of mail (ie. dive mail, sky mail, etc)
        self.set_thumbnail(url="https://i.imgur.com/BR7T4zp.png")

    def init_fields(self, mail):
        self.add_field(
            name="\u200b",
            value="__Body:__\n"
            + mail.message[:800]
            + "\n----------------------------------------",
        )


class MailHomeView(disnake.ui.View):
    def __init__(self, bot, inter_author, user):
        super().__init__()
        self.bot = bot
        self.inter_author = inter_author
        self.user = user
        self.next = ""
        self.interaction = None

    @disnake.ui.button(label="Inbox", style=disnake.ButtonStyle.grey, emoji="📫")
    async def inbox_button_press(
        self, button: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        if not await verify_author(self.inter_author, interaction):
            return
        self.next = "inbox"
        self.interaction = interaction
        self.stop()

    @disnake.ui.button(label="Send New Mail", style=disnake.ButtonStyle.grey, emoji="📨")
    async def send_button_press(
        self, button: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        if not await verify_author(self.inter_author, interaction):
            return
        await interaction.response.send_modal(modal=SendModal(self.bot, self.user))


class InboxView(disnake.ui.View):
    def __init__(self, bot, inter_author, user, page_offset):
        super().__init__()
        self.user = user
        self.inter_author = inter_author
        self.page_offset = page_offset
        self.bot = bot
        self.mail = None
        self.interaction = None
        self.next = ""
        self.max_pages = math.ceil(len(self.user.mailbox.sort_mailbox_by_date()) / 5)
        self.update_buttons()

    def update_buttons(self):
        for x in range(5):
            index = x + self.page_offset * 5
            if index < len(self.user.mailbox.sort_mailbox_by_date()):
                self.children[x].disabled = False
            else:
                self.children[x].disabled = True
        if len(self.user.mailbox.sort_mailbox_by_date()) <= 5:
            self.children[5].disabled = True
            self.children[6].disabled = True
        else:
            self.children[5].disabled = False
            self.children[6].disabled = False

    @disnake.ui.button(label="\u200b", style=disnake.ButtonStyle.grey, emoji="1️⃣")
    async def one_button_press(
        self, button: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        await self.read_mail(1, interaction)

    @disnake.ui.button(label="\u200b", style=disnake.ButtonStyle.grey, emoji="2️⃣")
    async def two_button_press(
        self, button: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        await self.read_mail(2, interaction)

    @disnake.ui.button(label="\u200b", style=disnake.ButtonStyle.grey, emoji="3️⃣")
    async def three_button_press(
        self, button: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        await self.read_mail(3, interaction)

    @disnake.ui.button(label="\u200b", style=disnake.ButtonStyle.grey, emoji="4️⃣")
    async def four_button_press(
        self, button: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        await self.read_mail(4, interaction)

    @disnake.ui.button(label="\u200b", style=disnake.ButtonStyle.grey, emoji="5️⃣")
    async def five_button_press(
        self, button: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        await self.read_mail(5, interaction)

    @disnake.ui.button(label="\u200b", style=disnake.ButtonStyle.grey, emoji="⬅️")
    async def left_button_press(
        self, button: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        if not await verify_author(self.inter_author, interaction):
            return
        self.page_offset -= 1
        if self.page_offset < 0:
            self.page_offset = self.max_pages - 1
        self.update_buttons()
        self.interaction = interaction
        self.next = "inbox"
        self.stop()

    @disnake.ui.button(label="\u200b", style=disnake.ButtonStyle.grey, emoji="➡️")
    async def right_button_press(
        self, button: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        if not await verify_author(self.inter_author, interaction):
            return
        self.page_offset += 1
        if self.page_offset > self.max_pages - 1:
            self.page_offset = 0
        self.update_buttons()
        self.interaction = interaction
        self.next = "inbox"
        self.stop()

    @disnake.ui.button(label="Home", style=disnake.ButtonStyle.grey, emoji="↩️")
    async def back_button_press(
        self, button: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        if not await verify_author(self.inter_author, interaction):
            return
        self.interaction = interaction
        self.next = "home"
        self.stop()

    async def read_mail(self, button_number, interaction):
        if not await verify_author(self.inter_author, interaction):
            return
        index = button_number - 1 + self.page_offset * 5
        self.mail = self.user.mailbox.sort_mailbox_by_date()[index]
        self.interaction = interaction
        self.next = "read mail"
        self.stop()


class MailReadView(disnake.ui.View):
    def __init__(self, bot, inter_author, user, mail, page_offset):
        super().__init__()
        self.user = user
        self.mail = mail
        self.inter_author = inter_author
        self.page_offset = page_offset
        self.bot = bot
        self.interaction = None
        self.next = ""
        self.update_buttons()

    def update_buttons(self):
        if not self.mail.has_attachments():
            self.children[1].disabled = True
            self.children[2].disabled = False
        else:
            self.children[1].disabled = False
            self.children[2].disabled = True

    @disnake.ui.button(label="Reply", style=disnake.ButtonStyle.grey, emoji="📨")
    async def reply_button_press(
        self, button: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        if not await verify_author(self.inter_author, interaction):
            return
        await interaction.response.send_modal(modal=SendModal(self.bot, self.user, self.mail.from_id))

    @disnake.ui.button(label="Claim all attachments", style=disnake.ButtonStyle.grey)
    async def claim_button_press(
        self, button: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        if not await verify_author(self.inter_author, interaction):
            return
        if self.mail.has_attachments():
            await self.user.claim_all_mail_attachments(self.mail)
            self.update_buttons()
            self.interaction = interaction
            self.next = "read mail"
            self.stop()
        else:
            await interaction.response.defer()

    @disnake.ui.button(label="Delete", style=disnake.ButtonStyle.grey, emoji="❌")
    async def delete_button_press(
        self, button: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        if not await verify_author(self.inter_author, interaction):
            return
        await self.user.delete_mail(self.mail.unique_id)
        self.page_offset = 0
        self.interaction = interaction
        self.next = "inbox"
        self.stop()

    @disnake.ui.button(label="Inbox", style=disnake.ButtonStyle.grey, emoji="↩️")
    async def back_button_press(
        self, button: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        if not await verify_author(self.inter_author, interaction):
            return
        self.interaction = interaction
        self.next = "inbox"
        self.stop()


class SendModal(disnake.ui.Modal):
    def __init__(self, bot, user, to_id: int = 0):
        # TODO: Support attachments of items and Pokemon
        # TODO: Remove temporary testing dict
        self.user = user
        self.bot = bot
        components = []
        if to_id == 0:
            components.append(
                disnake.ui.TextInput(
                    label="To:",
                    placeholder="Enter the Discord name or ID.",
                    custom_id="to",
                    style=disnake.TextInputStyle.short,
                    max_length=50,
                )
            )
        else:
            components.append(
                disnake.ui.TextInput(
                    label="To:",
                    value=str(to_id),
                    custom_id="to",
                    style=disnake.TextInputStyle.short,
                    max_length=50,
                )
            )
        components.append(
            disnake.ui.TextInput(
                label="Subject",
                placeholder="Enter the subject line of your message here.",
                custom_id="subject",
                style=disnake.TextInputStyle.short,
                max_length=50,
            )
        )
        components.append(
            disnake.ui.TextInput(
                label="Message",
                placeholder="Enter your message here.",
                custom_id="message",
                style=disnake.TextInputStyle.paragraph,
                max_length=800,
            )
        )
        super().__init__(
            title="Send a New Message",
            custom_id="send_message",
            components=components,
        )

    async def callback(self, inter: disnake.ModalInteraction):
        # Todo update with actual database of users, will need to fetch user and their mailbox
        embed = disnake.Embed(title="Message sent!")
        to = inter.text_values["to"]
        subject = inter.text_values["subject"]
        message = inter.text_values["message"]
        to_user = await self.bot.user_database.get_user(to)
        if to_user:
            mail = Mail(self.user.identifier, self.user.author_name, to_user.identifier, subject, message)
            await to_user.receive_mail(mail)
            discord_member = self.bot.get_user(to)
            try:
                await discord_member.send(
                    "You have new mail! View it in your mailbox now with `/mail`!"
                )
            except:
                pass
            for key, value in inter.text_values.items():
                if key == "to":
                    new_value = to_user.author_name
                else:
                    new_value = value[:1024]
                embed.add_field(
                    name=key.capitalize(),
                    value=new_value,
                    inline=False,
                )
            embed.set_thumbnail(url="https://i.imgur.com/BR7T4zp.png")
            embed.set_footer(
                text=f"Message sent by {inter.author}",
                icon_url=inter.author.display_avatar,
            )
            await inter.response.send_message(embed=embed, ephemeral=True)
        else:
            await inter.response.send_message("User not found.")


async def verify_author(inter_author, interaction):
    if interaction.author != inter_author:
        await interaction.response.send_message(
            "Sorry this mailbox is for: "
            + inter_author.name
            + "\nPlease request your own mailbox with `/mail`!",
            ephemeral=True,
        )
        return False
    return True


# TODO: Test setup removal
# zetaroid_mailbox = MailBox(189312357892096000)
# new_mail = Mail(189312357892096000, 189312357892096000, "Subject 1", "Test mail 1")
# time.sleep(2)
# new_mail_2 = Mail(189312357892096000, 189312357892096000, "Subject 2", "Test mail 2")
# new_mail_2.add_item("TEST ITEM")
# time.sleep(2)
# new_mail_3 = Mail(189312357892096000, 189312357892096000, "Subject 3", "Test mail 3")
# time.sleep(2)
# new_mail_4 = Mail(189312357892096000, 189312357892096000, "Subject 4", "Test mail 4")
# new_mail_4.add_pokemon("TEST POKEMON")
# time.sleep(2)
# new_mail_5 = Mail(189312357892096000, 189312357892096000, "Subject 5", "Test mail 5")
# time.sleep(2)
# new_mail_7 = Mail(189312357892096000, 189312357892096000, "Subject 6", "Test mail 6")
# mail_str = new_mail_7.to_string()
# print(mail_str)
# new_mail_6 = Mail()
# new_mail_6.from_string(mail_str)
# new_mail_6.add_item("TEST ITEM")
# new_mail_6.add_pokemon("TEST POKEMON")
# zetaroid_mailbox.add_mail(new_mail_3)
# zetaroid_mailbox.add_mail(new_mail)
# zetaroid_mailbox.add_mail(new_mail_5)
# zetaroid_mailbox.add_mail(new_mail_6)
# zetaroid_mailbox.add_mail(new_mail_4)
# zetaroid_mailbox.add_mail(new_mail_2)
# mailbox_str = zetaroid_mailbox.to_string()
# new_zetaroid_mailbox = MailBox()
# new_zetaroid_mailbox.from_string(mailbox_str)
# mailbox_dict = {
#     580034015759826944: MailBox(580034015759826944),
#     189312357892096000: new_zetaroid_mailbox,
#     775243228311191572: MailBox(775243228311191572),
#     735830204286763148: MailBox(735830204286763148),
#     928979024812867614: MailBox(928979024812867614),
#     716840809353314344: MailBox(716840809353314344),
#     404418440187740171: MailBox(404418440187740171),
#     710910223698624513: MailBox(710910223698624513),
#     942293716410982462: MailBox(942293716410982462),
#     533591507744325642: MailBox(533591507744325642),
#     246135956007157762: MailBox(246135956007157762),
#     311977451116822540: MailBox(311977451116822540),
# }
