import discord
import regex as re
import os
from validator import *
import traceback
from db import DB

VALID_BLOCKCHAINS = ['eth', 'sol', 'ada', 'matic']


class InvalidCommand(Exception):
    """
    An exception to be thrown when an invalid command is encountered
    """

    def __init__(self):
        pass


class WhitelistClient(discord.Client):
    """
    The discord client which manages all guilds and corrosponding data
    """

    def __init__(self, db: DB, *, loop=None, **options):
        """
        Args:
            data (dict): A data dictionary stored in memory.
        """
        super().__init__(loop=loop, **options)
        self.db = db
        self.data = {}
        self.admin_commands = {
            'channel': self.set_whitelist_channel,
            'role': self.set_whitelist_role,
            'blockchain': self.set_blockchain,
            'data': self.get_data,  
            'config': self.get_config,
            'clear': self.clear_data,
            'help.admin': self.help_admin
        }
        self.public_commands = {
            'help': self.help,
            'check': self.check
        }
        self.validators = {
            'eth': validate_eth,
            'sol': validate_sol,
            'ada': validate_ada,
            'matic': validate_matic
        }
        self.regex = {
            'channel': re.compile(">channel <#\d+>$"),
            'role': re.compile(">role <@&\d+>$"),
            'blockchain': re.compile(">blockchain \w{3}")
        }

    def _log(self, head: str, text: str) -> None:
        with open('log.txt', 'a+') as log:
            log.write(f"Head: {head}\n   Text: {str(text)}\n\n")

    async def on_ready(self) -> None:
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print("Initialising...")
        async for guild in self.fetch_guilds():
            if self.db.execute('SELECT * FROM discord_server WHERE id=?', (guild.id,)).fetchone() is None:
                print(f"Adding guild '{str(guild)}' to database.")
                self.db.execute(
                    "INSERT INTO discord_server VALUES (?,?,?,?)", (guild.id, None, None, None))
                self.db.commit()
        print("-------------")

    async def set_whitelist_channel(self, message: discord.Message) -> None:
        """ Handles setting the channel that will be used for whitelisting

        Args:
            message (discord.Message): The discord message containing the command request

        Raises:
            InvalidCommand: The message structure was not as expected.
        """
        channels = message.channel_mentions
        if len(channels) != 1 or not self.regex['channel'].fullmatch(message.content):
            raise InvalidCommand()

        self.db.execute("UPDATE discord_server SET whitelist_channel = ? WHERE id = ?",
                        (channels[0].id, message.guild.id))
        self.db.commit()

        await message.reply(f"Canal de la whitelist cambiado correctamente a <#{channels[0].id}>",
                            mention_author=True)

    async def set_whitelist_role(self, message: discord.Message) -> None:
        """ Handles setting the role that will be used for whitelisting

        Args:
            message (discord.Message): The discord message containing the command request

        Raises:
            InvalidCommand: The message structure was not as expected.
        """
        roles = message.role_mentions
        if len(roles) != 1 or not self.regex['role'].fullmatch(message.content):
            raise InvalidCommand()

        self.db.execute("UPDATE discord_server SET whitelist_role = ? WHERE id = ?",
                        (roles[0].id, message.guild.id))
        self.db.commit()

        await message.reply(f"Rol de la whitelist cambiado correctamente a <@&{roles[0].id}>",
                            mention_author=True)

    async def set_blockchain(self, message: discord.Message) -> None:
        """ Handles setting the blockchain that will be used for validating wallet addresses.

        Args:
            message (discord.Message): The discord message containing the command request

        Raises:
            InvalidCommand: The message structure was not as expected.
        """
        code = message.content[-3:]
        if code in VALID_BLOCKCHAINS:

            self.db.execute(
                "UPDATE discord_server SET blockchain = ? WHERE id = ?", (code, message.guild.id))
            self.db.commit()

            await message.reply(f"Blockchain cambiada correctamente a `{code}`", mention_author=True)
        else:
            raise InvalidCommand()

    async def get_config(self, message: discord.Message) -> None:
        """ Returns the current config of a given server to the user.

        Args:
            message (discord.Message): The discord message that sent the request.
        """
        row = self.db.execute(
            "SELECT * FROM discord_server WHERE id = ?", (message.guild.id,)).fetchone()
        if row is None:
            return
        replyStr = f"""
        Canal de la whitelist: {"None" if row["whitelist_channel"] is None else f"<#{row['whitelist_channel']}>"}
        Rol de la whitelist: {"None" if row["whitelist_role"] is None else f"<@&{row['whitelist_role']}>"}
        Blockchain: {row['blockchain']}
        """
        reply = discord.Embed(
            title=f'Configuración para {message.guild}', description=replyStr)

        await message.reply(embed=reply, mention_author=True)

    async def get_data(self, message: discord.Message) -> None:
        """ Sends a CSV file to the user containing the current data stored by the bot

        Args:
            message (discord.Message): The discord message that sent the request.
        """
        file_name = f'{message.guild.id}.csv'
        with open(file_name, 'w+') as out_file:
            out_file.write('userId, walletAddress\n')
            out_file.writelines(
                map(lambda t: f"{t['id']},{t['wallet']}\n", self.db.execute("SELECT id, wallet FROM user WHERE discord_server = ?", (message.guild.id,)).fetchall()))
            out_file.flush()
        await message.reply('Los datos del servidor están adjuntos.',
                            file=discord.File(file_name))
        os.remove(file_name)

    async def clear_data(self, message: discord.Message) -> None:
        """ Clears the data and config currently stored by the bot regarding the current server

        Args:
            message (discord.Message): The discord message that sent the request.
        """
        self.db.execute(
            "DELETE FROM discord_server WHERE id = ?", (message.guild.id,))
        self.db.execute("INSERT INTO discord_server VALUES (?,?,?,?)",
                        (message.guild.id, None, None, None))
        self.db.commit()
        await message.reply("La información del servidor ha sido borrada.")

    async def help_admin(self, message: discord.Message) -> None:
        """ Returns a window that provides some help messages regarding how to use the bot for an admin.

        Args:
            message (discord.Message): The discord message that sent the request.
        """
        msg = discord.Embed(title="Ayuda (Admin)")
        desc = "Whitelist Manager es un bot diseñado para ayudar en la recolección de direcciones de wallet para whitelists o drops de NFTs.\nTras configurar el bot, los usuarios con el rol seleccionado podrán registrar las direcciones de sus wallets, las cuales podrás descargar luego en formato CSV.\nNota, la configuración debe estar completa para que el bot funcione."
        body = "`>channel #NombreDelCanal`: Selecciona el canal en el que el bot leerá las direcciones de wallets.\n`>role @NombreDelRol`: Selecciona el rol que debe poseer un usuario para poder añadir su wallet al registro de la whitelist.\n`>blockchain eth/sol/ada/matic`: Selecciona en que blockchain se va a trabajar. Esto permitira validar las direcciones de wallets que se añadan.\n`>config`: Ver la configuración actual del servidor.\n`>data`: Obtener la whitelist completa en formato CSV.\n`>clear`: Limpia la configuración y los datos de este servidor.\n`>help.admin`: Esta pantalla.\n`>help`: Pantalla general de ayuda."
        msg.description = desc
        msg.add_field(name="COMMANDS", value=body)
        await message.reply(embed=msg)

    async def help(self, message: discord.Message) -> None:
        """ Returns a window that provides some help messages regarding how to use the bot.

        Args:
            message (discord.Message): The discord message that sent the request.
        """
        msg = discord.Embed(title="Ayuda")
        desc = "Whitelist Manager es un bot diseñado para ayudar en la recolección de direcciones de wallet para whitelists o drops de NFTs."
        body = "`>check`: Te dirá si la durección de tu wallet ha sido registrada o no.\n`>help`: Esta ayuda.\n\nComo usar: Envia la dirección PUBLICA de tu wallet en el canal asignado para registrarla.\nEl mensaje debe contener unicamente la dirección de la wallet (sin `>` ni otros elementos)."
        msg.description = desc
        msg.add_field(name="COMMANDS", value=body)
        await message.reply(embed=msg)

    async def check(self, message: discord.Message) -> None:
        row = db.execute("SELECT * FROM user WHERE id = ? AND discord_server = ?",
                         (message.author.id, message.guild.id)).fetchone()
        if row is not None:
            await message.reply(f"¡Tu wallet está registrada! Los ultimos 3 caracteres son: `{row['wallet'][-3:]}`")
        else:
            await message.reply(f"Tu wallet no esta registrada. Usa `>help` para mas información.")

    async def on_message(self, message: discord.Message) -> None:
        """ Responds to the 'on_message' event. Runs the appropriate commands given the user has valid privellages.

        Args:
            message (discord.Message): The discord message that sent the request.
        """

        try:
            # we do not want the bot to reply to itself
            if message.author.bot or not isinstance(message.author, discord.member.Member):
                return

            # Handle commands
            if message.author.guild_permissions.administrator and message.content.startswith(">"):
                command = message.content.split()[0][1:]
                if command in self.admin_commands.keys():
                    try:
                        await self.admin_commands[command](message)
                        return
                    except InvalidCommand:
                        await message.reply("Invalid command argument.", mention_author=True)
                    return
                if command in self.public_commands.keys():
                    try:
                        await self.public_commands[command](message)
                        return
                    except InvalidCommand:
                        await message.reply("Invalid command argument.", mention_author=True)
                    return

            # Handle whitelist additions
            server = self.db.execute(
                "SELECT * FROM discord_server WHERE id =?", (message.guild.id,)).fetchone()
            if (message.channel.id == server["whitelist_channel"] and server["whitelist_role"] in map(lambda x: x.id, message.author.roles)):
                if message.content.startswith('>'):
                    command = message.content.split()[0][1:]
                    if command in self.public_commands.keys():
                        try:
                            await self.public_commands[command](message)
                            return
                        except InvalidCommand:
                            await message.reply("Invalid command argument.", mention_author=True)
                    else:
                        commands = str(list(self.public_commands.keys()))[
                            1:-1].replace("'", "`")
                        await message.reply(f'Los comandos aceptados son: {commands}, usa `>help` para mas información.')
                    return
                
                if server["blockchain"] is None: return

                if self.validators[server["blockchain"]](message.content):
                    db.execute("DELETE FROM user WHERE id = ? and discord_server = ?", (message.author.id, message.guild.id))
                    db.execute("INSERT INTO user (id, discord_server, wallet) VALUES (?, ?, ?)", (message.author.id, message.guild.id, message.content))
                    db.commit()
                    await message.reply(
                        f"<@{message.author.id}> tu wallet terminada en `{message.content[-3:]}` ha sido validada y guardada.", mention_author=True)
                else:
                    await message.reply(f"La wallet terminada en `{message.content[-3:]}` es invalida.")
                
                await message.delete()
        except Exception:
            tb = traceback.format_exc()
            exception_string = tb.replace('\n', '---')
            self._log(exception_string,
                      f"{message}\nContent:   {message.content}")

    async def on_guild_join(self, guild: discord.Guild) -> None:
        """ Initialises a server when the bot joins

        Args:
            guild (discord.Guild): The guild that the server has joined

        """
        if db.execute("SELECT * FROM discord_server WHERE id=?", (guild.id,)).fetchone() is None:
            db.execute("INSERT INTO discord_server VALUES (?,?,?,?)", (guild.id, None, None, None))
            db.commit()

        self._log("New Guild", f"{guild.id}, {guild.name}")


if __name__ == '__main__':
    access_token = os.environ["ACCESS_TOKEN"]
    db = DB('data.db')
    client = WhitelistClient(db)
    client.run(access_token)