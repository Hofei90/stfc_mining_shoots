import toml
from discord.ext import commands
import discord
import pathlib
from peewee import SqliteDatabase, fn
import db_model as db
import datetime
from dataclasses import dataclass
import matplotlib.pyplot as plt
import asyncio

SKRIPTPFAD = pathlib.Path(__file__).parent
CONFIG = toml.load(SKRIPTPFAD / "config.toml")
CONFIG.update(toml.load(SKRIPTPFAD / "texte.toml"))

bot = commands.Bot(command_prefix="!")

db.DB_PROXY.initialize(SqliteDatabase(SKRIPTPFAD / "mining_shoots.db3"))
db.create_tables()


@dataclass
class UCShoot:
    date: datetime.date
    allianz: str
    enemy: str
    player: str


def check_input_allianz(input_):
    if any(character.isdigit() for character in input_):
        raise ValueError(f"digit in {input_!r} not allowed")


def check_user(userid):
    return db.User.get_or_none(db.User.userid == userid)


def get_or_create_unbekannter_user():
    user, _ = db.User.get_or_create(userid=1, name="unbekannter_user")
    user.datum = datetime.datetime.now()
    user.save()
    return user


def create_uc_shoot(user, daten):
    if len(daten) == 2:
        allianz = daten[0]
        check_input_allianz(allianz)
        uc_shoot = UCShoot(
            date=datetime.date.today(),
            allianz=allianz,
            enemy=daten[1],
            player=user
        )
    elif len(daten) == 3:
        allianz = daten[1]
        check_input_allianz(allianz)
        uc_shoot = UCShoot(
            date=datetime.datetime.strptime(daten[0], "%d.%m.%Y").date(),
            allianz=daten[1],
            enemy=daten[2],
            player=user
        )
    else:
        uc_shoot = None
    return uc_shoot


def schreibe_in_datenbank(daten):
    db.UCShoots.create(
        date=daten.date,
        allianz=daten.allianz.upper(),
        enemy=daten.enemy.lower(),
        player=daten.player
    )


def load_players():
    query = (db.UCShoots
             .select(db.UCShoots, fn.COUNT(db.UCShoots.enemy).alias("enemy_count"))
             .group_by(db.UCShoots.enemy))
    return query


def load_players_time(tage=60):
    query = (db.UCShoots
             .select(db.UCShoots, fn.COUNT(db.UCShoots.enemy).alias("enemy_count"))
             .group_by(db.UCShoots.enemy)
             .where(db.UCShoots.date >= datetime.date.today() - datetime.timedelta(days=tage)))
    return query


def load_allys():
    query = (db.UCShoots
             .select(db.UCShoots, fn.COUNT(db.UCShoots.enemy).alias("enemy_count"))
             .group_by(db.UCShoots.allianz))
    return query


def load_allys_time(tage=60):
    query = (db.UCShoots
             .select(db.UCShoots, fn.COUNT(db.UCShoots.enemy).alias("enemy_count"))
             .group_by(db.UCShoots.allianz)
             .where(db.UCShoots.date >= datetime.date.today() - datetime.timedelta(days=tage)))
    return query


@bot.command(name="reg",
             help=CONFIG["texte"]["reg"]["help"],
             brief=CONFIG["texte"]["reg"]["brief"])
async def user_registrieren(ctx):
    channel = ctx.channel
    author = ctx.author
    await ctx.channel.send(CONFIG["texte"]["reg"]["zustimmung_text"])

    def check(m):
        return m.content.lower() == CONFIG["texte"]["reg"][
            "zustimmung_antwort"].lower() and m.channel == channel and m.author == author

    try:
        msg = await bot.wait_for('message', timeout=60*2, check=check)
    except asyncio.TimeoutError:
        await channel.send('👎 - Timeout')
    else:
        if msg.content.lower() == CONFIG["texte"]["reg"]["zustimmung_antwort"].lower():
            db.User.get_or_create(userid=ctx.author.id, name=ctx.author.name, datum=datetime.datetime.now())
            await ctx.channel.send('Benutzer registriert, Bot kann nun verwendet werden')


@bot.command(name="del",
             help=CONFIG["texte"]["del"]["help"],
             brief=CONFIG["texte"]["del"]["brief"])
async def user_loeschen(ctx):
    user = check_user(ctx.author.id)
    if user is not None:
        channel = ctx.channel
        author = ctx.author
        await ctx.channel.send(CONFIG["texte"]["del"]["text"])

        def check(m):
            return m.content.lower() in CONFIG["texte"]["del"][
                "antworten"] and m.channel == channel and m.author == author

        try:
            msg = await bot.wait_for('message', timeout=60 * 2, check=check)
        except asyncio.TimeoutError:
            await channel.send('👎 - Timeout')
        else:
            if msg.content.lower() == "ja":
                user = check_user(ctx.author.id)
                unbekannter_user = get_or_create_unbekannter_user()
                db.UCShoots.update(player=unbekannter_user).where(db.UCShoots.player == user).execute()
                db.User.delete().where(db.User.userid == user.userid).execute()
                await ctx.channel.send('Benutzer gelöscht')
            else:
                await ctx.channel.send('Löschung abgebrochen')
    else:
        await ctx.channel.send("Benutzer unbekannt")


@bot.command(name="dia",
             help=CONFIG["texte"]["dia"]["help"],
             brief=CONFIG["texte"]["dia"]["brief"])
async def kuchen_backen(ctx, *args):
    user = check_user(ctx.author.id)
    if user is not None:
        labels = []
        values = []
        if args:
            if args[0] == "all":
                player_stat = load_allys()
            else:
                try:
                    tage = int(args[0])
                except ValueError:
                    await ctx.send("Nur Zahlen senden")
                    return
                else:
                    player_stat = load_allys_time(tage)
        else:
            player_stat = load_allys_time()
        if not player_stat:
            await ctx.send("Keine Einträge vorhanden")
            return
        for datum in player_stat:
            labels.append(datum.allianz)
            values.append(datum.enemy_count)
        fig1, ax1 = plt.subplots()
        ax1.pie(values, labels=labels, autopct='%1.1f%%')
        ax1.axis('equal')
        picpfad = pathlib.Path(SKRIPTPFAD / CONFIG["pic"])
        plt.savefig(picpfad)
        await ctx.send(file=discord.File(picpfad))
    else:
        await ctx.send(CONFIG["texte"]["nicht_registiert"])


@bot.command(name="uca",
             help=CONFIG["texte"]["uca"]["help"],
             brief=CONFIG["texte"]["uca"]["brief"])
async def show_ally_stat(ctx, *args):
    user = check_user(ctx.author.id)
    if user is not None:
        if args:
            if args[0] == "all":
                player_stat = load_allys()
            else:
                try:
                    tage = int(args[0])
                except ValueError:
                    await ctx.send("Nur Zahlen senden")
                    return
                else:
                    player_stat = load_allys_time(tage)
        else:
            player_stat = load_allys_time()
        if player_stat:
            await ctx.send(
                "\n".join(
                    f"{datum.allianz}: {datum.enemy_count}"
                    for datum in player_stat
                )
            )
        else:
            await ctx.send("Keine Einträge vorhanden")
    else:
        await ctx.send(CONFIG["texte"]["nicht_registiert"])


@bot.command(name="ucp",
             help=CONFIG["texte"]["ucp"]["help"],
             brief=CONFIG["texte"]["ucp"]["brief"])
async def show_player_stat(ctx, *args):
    user = check_user(ctx.author.id)
    if user is not None:
        if args:
            if args[0] == "all":
                player_stat = load_players()
            else:
                try:
                    tage = int(args[0])
                except ValueError:
                    await ctx.send("Nur Zahlen senden")
                    return
                else:
                    player_stat = load_players_time(tage)
        else:
            player_stat = load_players_time()
        if player_stat:
            await ctx.send(
                "\n".join(
                    f"[{datum.allianz}]{datum.enemy}: {datum.enemy_count}"
                    for datum in player_stat
                )
            )
        else:
            await ctx.send("Keine Einträge vorhanden")
    else:
        await ctx.send(CONFIG["texte"]["nicht_registiert"])


@bot.command(name="uc",
             help=CONFIG["texte"]["uc"]["help"],
             brief=CONFIG["texte"]["uc"]["brief"]
             )
async def add_uc_shoot(ctx, *args):
    user = check_user(ctx.author.id)
    if user is not None:
        try:
            uc_shoot = create_uc_shoot(user, args)
        except ValueError:
            uc_shoot = None
        if uc_shoot is not None:
            schreibe_in_datenbank(uc_shoot)
            await ctx.send(f"UC Abschuss gespeichert")
        else:
            await ctx.send("Ungültiges Format")
    else:
        await ctx.send(CONFIG["texte"]["nicht_registiert"])


bot.run(CONFIG["token"])

