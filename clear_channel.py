import pathlib
import sys

import discord
import matplotlib.pyplot as plt
import toml

from mining_shoots_discord import load_players_time, load_allys_time

SKRIPTPFAD = pathlib.Path(__file__).parent
CONFIG = toml.load(SKRIPTPFAD / "config.toml")
CONFIG.update(toml.load(SKRIPTPFAD / "texte.toml"))

WORK_CHANNEL_NAME = "uc-abschüsse"

client = discord.Client()


def search_work_channel(work_channel_name):
    channels = client.get_all_channels()
    work_channel = None
    for channel in channels:
        if str(channel) == work_channel_name:
            work_channel = client.get_channel(channel.id)
            print(work_channel)
            break
    return work_channel


async def delete_messages(work_channel):
    messages = True
    while messages:
        messages = await work_channel.history().flatten()
        for message in messages:
            print(f"{message.id}:{message.content}")
            await message.delete()


async def show_player_stat(work_channel):
    player_stat = load_players_time()
    if player_stat:
        await work_channel.send(
            "\n".join(
                f"[{datum.allianz}]{datum.enemy}: {datum.enemy_count}"
                for datum in player_stat
            )
        )
    else:
        await work_channel.send("Keine Einträge vorhanden")


async def show_ally_stat(work_channel):
    player_stat = load_allys_time()
    print(player_stat)
    print(work_channel)
    if player_stat:
        await work_channel.send(
            "\n".join(
                f"{datum.allianz}: {datum.enemy_count}"
                for datum in player_stat
            )
        )
    else:
        await work_channel.send("Keine Einträge vorhanden")


async def dia_erstellen(work_channel):
    labels = []
    values = []
    player_stat = load_allys_time()

    if player_stat:
        for datum in player_stat:
            labels.append(datum.allianz)
            values.append(datum.enemy_count)
        fig1, ax1 = plt.subplots()
        ax1.pie(values, labels=labels, autopct='%1.1f%%')
        ax1.axis('equal')
        picpfad = pathlib.Path(SKRIPTPFAD / CONFIG["pic"])
        plt.savefig(picpfad)
        await work_channel.send(file=discord.File(picpfad))
    else:
        await work_channel.send("Keine Einträge vorhanden")


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    work_channel = search_work_channel(WORK_CHANNEL_NAME)

    if work_channel is not None:
        await delete_messages(work_channel)
        await work_channel.send(CONFIG["bot_first_text"]["text"])
        await show_player_stat(work_channel)
        await show_ally_stat(work_channel)
        await dia_erstellen(work_channel)
        await client.close()
        sys.exit(0)
    else:
        await client.close()
        sys.exit(1)

if __name__ == "__main__":
    client.run(CONFIG["token"])
