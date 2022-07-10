##imports
import asyncio
import discord
import dotenv
import json
import os
import pytube
import random
from discord.ext import commands
from dotenv import load_dotenv
from math import floor
from pytube import Search
from pytube import YouTube
from time import sleep

##dotenv
load_dotenv()
TOKEN = os.getenv('TOKEN')
PATH = os.getenv('PROJECTPATH')

##global vars
queue = []
removed = None

def getSongName(filepath):
    filepath = filepath.replace(PATH, "")
    filepath = filepath.replace(".webm", "")
    return filepath

def play_next(voice_channel, ctx, media=None):
    global removed

    if voice_channel.is_playing():
        voice_channel.stop()
    
    try:
        os.remove(removed)
    except Exception as e:
        pass

    else:
        if len(queue) >= 1:
            media = queue.pop(0)
            removed = media
            voice_channel.play(discord.FFmpegPCMAudio(executable="ffmpeg.exe", source=media), after=lambda e: play_next(voice_channel, ctx, media))
            asyncio.run_coroutine_threadsafe(ctx.send("Now Playing: {}".format(getSongName(media))), bot.loop)
        
        else:
            if not voice_channel.is_playing():
                sleep(300)
                asyncio.run_coroutine_threadsafe(voice_channel.disconnect(), bot.loop)
                asyncio.run_coroutine_threadsafe(ctx.send("Leaving channel because there's no more life here"), bot.loop)

async def play_song(voice_channel, ctx, media):
    if voice_channel.is_playing():
        queue.append(media)
        await ctx.send('Song Queued: {}'.format(getSongName(media)))
    else:
        global removed
        removed = media
        voice_channel.play(discord.FFmpegPCMAudio(executable="ffmpeg.exe", source=media), after=lambda e: play_next(voice_channel, ctx, media))
        await ctx.send("Now Playing: {}".format(getSongName(media)))

async def status_task():
    while True:
        load_dotenv(override=True)
        STATUS = os.getenv('STATUS')
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=random.choice(json.loads(STATUS))))
        await asyncio.sleep(10)

##bot events
bot = commands.Bot(command_prefix='!')
@bot.event
async def on_ready():
    print("Bot running")
    bot.loop.create_task(status_task())

@bot.event
async def on_guild_join(guild):
    print("{} - {}".format(guild.id, guild.name))

##bot commands(play, search, queue, remove, skip, pause, resume)
@bot.command()
async def play(ctx, url):
    try:
        voice_channel = ctx.author.voice.channel

        yt = YouTube(url)
        selected = yt.streams.filter(only_audio=True).desc().first().download()
        
    except pytube.exceptions.LiveStreamError as e:
        await ctx.send("Cannot play livestream video!")

    except pytube.exceptions.HTMLParseError as e:
        await ctx.send("Failed to parse HTML, please try again")

    except pytube.exceptions.RegexMatchError as e:
        await ctx.send("**!play** only accept youtube url!")

    except AttributeError as e:
        await ctx.send("You should be in the voice channel first!") 

    except pytube.exceptions.PytubeError as e:
        await ctx.send("Something happened, please try again")

    except Exception as e:
        await ctx.send("Something happened, please try again")

    else:
        # waitMsg = await ctx.send("Please wait...")
        if ctx.voice_client is None:
            vc = await voice_channel.connect()
        else:
            vc = ctx.voice_client
        # await waitMsg.delete()
        await play_song(vc, ctx, selected) 

@bot.command()
async def search(ctx, *music):

    def convertLength(length):
        minutes = str(int(floor(length/60)))
        seconds = str(int(length%60))
        if len(minutes) == 1:
            minutes = str("0"+minutes)
        if len(seconds) == 1:
            seconds = str("0"+seconds) 
        return str(minutes+":"+seconds)

    search = Search(music)
    respond = ''
    limit=9
    for index,item in enumerate(search.results):
        respond += str('{}. {} ({})\n'.format(index+1, item.title, convertLength(item.length)))
        if index == limit:
            break
    
    listMsg = await ctx.send(respond)
    message = await bot.wait_for("message")
    while True:
        if message.content.isdigit():
            if 1 <= int(message.content) <= 10:
                break
            else:
                message = await bot.wait_for("message")
        else:
            message = await bot.wait_for("message")
    await listMsg.delete()

    author = ctx.author
    if message.author == author:
        try:
            voice_channel = message.author.voice.channel
            number = int(message.content)
            # waitMsg = await ctx.send("Please wait...")
            selected = search.results[number-1].streams.filter(only_audio=True).desc().first().download()
            if ctx.voice_client is None:
                vc = await voice_channel.connect()
            else:
                vc = ctx.voice_client
            # await waitMsg.delete()
            await play_song(vc, ctx, selected)

        except AttributeError as e:
            await ctx.send("You should be in the voice channel first!") 

        except pytube.exceptions.PytubeError as e:
            await ctx.send("Something happened, please try again")

        except Exception as e:
            await ctx.send("Something happened, please try again")          

@bot.command()
async def q(ctx):
    if len(queue) >= 1:
        respond = 'Queue for {}: \n'.format(ctx.channel)
        for index, q in enumerate(queue):
            respond += str('{}. {}\n'.format(index+1, getSongName(q)))
        await ctx.send(respond)
    else:
        await ctx.send("Empty queue")

@bot.command()
async def remove(ctx, index):
    if len(queue) >= 1:
        item = queue.pop(int(index)-1)
        try:
            os.remove(item)
        except Exception as e:
            pass
        await ctx.send("Removed {}".format(getSongName(item)))
    else:
        await ctx.send("There's nothing to remove")

@bot.command()
async def skip(ctx):
    play_next(ctx.voice_client, ctx)

@bot.command()
async def pause(ctx):
    if ctx.voice_client.is_playing(): 
        ctx.voice_client.pause()
        await ctx.send("Paused")
    else:
        await ctx.send("Already paused, please use !resume to resume")

@bot.command()
async def resume(ctx):
    if not ctx.voice_client.is_playing(): 
        ctx.voice_client.resume()
        await ctx.send("Resumed")
    else:
        await ctx.send("Already resumed, please use !pause to pause")

@bot.command()
async def status(ctx, *message):
    AUTHORID = os.getenv('AUTHORID')
    emojis = ['✅', '❌']

    if str(ctx.author.id) != AUTHORID:
        respond = await ctx.send("<@{}>, {} would like to add **{}** as a status".format(AUTHORID, ctx.author.mention, str(''.join(message))))
        for emoji in emojis:    
            await respond.add_reaction(emoji)

        try:
            reaction, user = await bot.wait_for('reaction_add', timeout=20)
        except asyncio.TimeoutError:
            await respond.delete()
            await ctx.send("Timeout")
        else:
            if str(user.id) == AUTHORID: 
                if str(reaction.emoji) == '✅' :
                    load_dotenv(override=True)
                    STATUS = json.loads(os.getenv('STATUS'))
                    if str(''.join(message)) in STATUS:
                        await ctx.send("**{}** already exists".format(str(''.join(message))))
                    else:
                        STATUS.append(message.content)
                        dotenv.set_key(".env", 'STATUS', json.dumps(STATUS))
                        await ctx.send("**{}** has been *added* to status!".format(str(''.join(message))))
                else:
                    await ctx.send("**{}** not accepted!".format(str(''.join(message))))
    else:
        load_dotenv(override=True)
        STATUS = json.loads(os.getenv('STATUS'))
        if str(''.join(message)) in STATUS:
            await ctx.send("**{}** already exists".format(str(''.join(message))))
        else:
            STATUS.append(str(''.join(message)))
            dotenv.set_key(".env", 'STATUS', json.dumps(STATUS))
            await ctx.send("**{}** has been *added* to status!".format(str(''.join(message))))

##debugging command
@bot.command()
async def test(ctx, *message):
    print(ctx)
    print(ctx.author)
    print(ctx.guild.id)
    print(ctx.channel)

##run bot
bot.run(TOKEN)