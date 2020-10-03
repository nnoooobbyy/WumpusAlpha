import aiohttp
import json
import asyncio
import inspect
import math
import sys
import os

from datetime import datetime
from colorama import init, Fore, Back, Style

from discord import Game
from discord import embeds
from discord import Intents
from discord import emoji as emj
from discord.ext import commands
from dotenv import load_dotenv

init()

# ----- VARIABLES
url = "http://api.wolframalpha.com/v2/query?"
activeMessages = {}
colors = {'n': Fore.LIGHTWHITE_EX, 's': Fore.LIGHTGREEN_EX, 'f': Fore.LIGHTRED_EX}
liveTime = datetime.now()
    
# env variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
appID = os.getenv('WOLFRAM_ID')

# ----- DEFINITIONS
# PRINT DEFS
# failure print
def fprint(message):
    caller = inspect.stack()[1][3]
    print(colors['f'] + f"{datetime.now().strftime('%H:%M:%S')} | {caller} | {message}" + colors['n'])

# success print
def sprint(message):
    caller = inspect.stack()[1][3]
    print(colors['s'] + f"{datetime.now().strftime('%H:%M:%S')} | {caller} | {message}" + colors['n'])

# neutral print
def nprint(message):
    caller = inspect.stack()[1][3]
    print(colors['n'] + f"{datetime.now().strftime('%H:%M:%S')} | {caller} | {message}")

# ASYNC DEFS
# waits a certain amount of time, then removes the messageID from active messages
async def removeAfterWait(messageID, messageLocation):
    await asyncio.sleep(30)
    del activeMessages[messageID]

# updates presence with latest query info
async def updatePresence():
    try:
        with open('queryCount.log', 'r') as rf:
            queries = rf.read()
        activity = Game(f"with {queries} answers")
        await bot.change_presence(activity=activity)
    except:
        fprint("presence update failed!")

# intent
intents = Intents.default()

bot = commands.AutoShardedBot(command_prefix='=', intents=intents)

# ----- BOT EVENTS
# triggered when bot is ready
@bot.event
async def on_ready():
    liveTime = datetime.now()
    sprint(f'{bot.user.name} ready at {liveTime.strftime("%Y-%m-%d %H:%M:%S")}')

# triggered when shard is ready
@bot.event
async def on_shard_ready(shard):
    sprint(f'shard {shard} ready at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')

# triggered when bot connects
@bot.event
async def on_connect():
    liveTime = datetime.now()
    sprint(f'{bot.user.name} connected to Discord at {liveTime.strftime("%Y-%m-%d %H:%M:%S")}')

# triggered when bot resumes
@bot.event
async def on_resumed():
    liveTime = datetime.now()
    sprint(f'{bot.user.name} resumed at {liveTime.strftime("%Y-%m-%d %H:%M:%S")}')

# triggered when bot is disconnected
@bot.event
async def on_disconnect():
    fprint(f'{bot.user.name} disconnected from Discord at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')

# triggered when an exception is raised
@bot.event
async def on_error(event, *args, **kwargs):
    with open('err.log', 'a') as f:
        fprint("!!! WARNING !!!\nexception raised! check err.log for more details")
        f.write(f'\nException raised at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        f.write(f'\n{sys.exc_info()}')

# triggered when an error occurs in a command
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.CommandNotFound) or isinstance(error, commands.errors.CommandInvokeError):
        return
    raise error

# triggered when a reaction is added
@bot.event
async def on_reaction_add(reaction, user):
    if user == bot.user:
        return

    if reaction.message.id in activeMessages:
        if reaction.emoji == "▶️" or reaction.emoji == "◀️":
            # settings variables
            fields = activeMessages[reaction.message.id]['fields']
            images = activeMessages[reaction.message.id]['images']
            embedTitle = activeMessages[reaction.message.id]['title']
            embedColor = activeMessages[reaction.message.id]['color']
            sentTime = activeMessages[reaction.message.id]['timestamp']
            response = activeMessages[reaction.message.id]['response']
            index = activeMessages[reaction.message.id]['index']
            if reaction.emoji == "▶️":
                if index == len(fields) - 1:
                    newIndex = 0
                else:
                    newIndex = index + 1
            elif reaction.emoji == "◀️":
                if index == 0:
                    newIndex = len(fields) - 1
                else: 
                    newIndex = index - 1

            updatedEmbed = embeds.Embed(title=embedTitle, colour=embedColor)
            embedFooter = f"{response} second response\n{newIndex + 1}/{len(fields)}"
            updatedEmbed.set_footer(text=embedFooter)
            updatedEmbed.add_field(name=fields[newIndex]['name'], value=f"```{fields[newIndex]['value']}```")
            updatedEmbed.set_image(url=images[newIndex])
            updatedEmbed.timestamp = sentTime
            await reaction.message.edit(embed=updatedEmbed)
            activeMessages[reaction.message.id] = {"fields": fields, "images": images, "title": embedTitle, "color": embedColor, "timestamp": sentTime, "response": response, "index": newIndex}
            if reaction.message.guild: await reaction.remove(user)

# ----- BOT COMMANDS
# =query - queries a question from Wolfram|Alpha
@bot.command(name='query', help='Queries a question from Wolfram|Alpha')
async def query(ctx):
    # VARIABLES
    reactionEmojis = ["◀️", "▶️"]
    fields = []
    images = []

    # OBTAINING QUERY
    question = ctx.message.content[len(ctx.prefix + ctx.command.name) + 1:]
    nprint(f"querying Wolfram|Alpha for '{question}'...")
    embedColor = embeds.Colour.lighter_grey()
    initialEmbed = embeds.Embed(title="preparing results...", colour=embedColor)
    responseMessage = await ctx.send(embed=initialEmbed)

    # WOLFRAM PROCESSING
    dataSet = {
    "appid": appID,
    "ip": "1.1.1.1",
    "input": question,
    "output": "json",
    "reinterpret": "true",
    "format": "image"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=dataSet) as resp:
            io = await resp.text()
            result = json.loads(io)

    # checking if query was successful
    if result['queryresult']['success'] == True:
        sprint(f"query for '{question}' successful! ({result['queryresult']['timing']} second response time)")
        embedColor = embeds.Colour.green()
        # walks through each pod in the results and creates fields from them
        for pod in result['queryresult']['pods']:
            # if input is in the pod's title, sets the embed title to it and continues
            if 'input' in pod['title'].lower():
                resultInput = pod['subpods'][0]['img']['title'].replace(" |", "")
                embedTitle = f'Results for "{resultInput}"'[:256]
                continue
            tempDict = {'name': "", 'value': ""}
            tempDict['name'] = f"{pod['title']}"
            # walks through each subpod and adds it to the same dict
            for subpod in range(pod['numsubpods']):
                if pod['subpods'][subpod]['img']['title']:
                    tempDict['value'] += f"\n{pod['subpods'][subpod]['img']['title']}"
                # if an image field has no text, that means it's an image so it creates a line
                else:
                    tempDict['value'] = " "
            # checking if a dict's value is all dashes, which signifies that it's an image
            #if re.search("^[-]*$", tempDict['value']):
            if tempDict['value'] == " ":
                ## idk how it knows which subpod it's talking about but it works so okay...
                images.append(pod['subpods'][subpod]['img']['src'])
            else:
                images.append(" ")
            fields.append(tempDict.copy())
        
        # adds to the amount of questions answered
        with open('queryCount.log', 'r') as rf:
            filedata = rf.read()
        count = int(filedata) + 1
        with open('queryCount.log', 'w') as wf:
            wf.write(str(count))
    else:
        fprint(f"query for '{question}' failed! ({result['queryresult']['timing']} second response time)")
        embedColor = embeds.Colour.red()
        embedTitle = "An error occured while obtaining results!"
        # loops through each 'data point' to find the reasons then adds them as fields
        for dataPoint in result['queryresult']:
            tempDict = {'name': "", 'value': ""}
            if dataPoint == 'didyoumeans':
                tempDict['name'] = "Did you mean"
                try:
                    for dym in result['queryresult']['didyoumeans']:
                        tempDict['value'] += f"\n{dym['val']}?"
                except:
                    tempDict['value'] = f"\n{result['queryresult']['didyoumeans']['val']}?"
            elif dataPoint == 'tips':
                tempDict['name'] = "Tips"
                try:
                    for tip in result['queryresult']['tips']:
                        tempDict['value'] += f"\n{tip['text']}?"
                except:
                    tempDict['value'] += f"\n{result['queryresult']['tips']['text']}"
            elif dataPoint == 'languagemsg':
                tempDict['name'] = "Language"
                tempDict['value'] += f"\n{result['queryresult']['languagemsg']['other']}"
            elif dataPoint == 'examplepage':
                tempDict['name'] = "Category"
                tempDict['value'] += "\nQuery is too vague!"
            elif dataPoint == 'futuretopic':
                tempDict['name'] = "Future topic"
                tempDict['value'] += f"\n{result['queryresult']['futuretopic']['msg']}"
            else:
                continue
            fields.append(tempDict.copy())
            images.append(" ")
        if fields == []:
            tempDict['name'] = "No known cause"
            tempDict['value'] = ":<"
            fields.append(tempDict.copy())
            images.append(" ")

    # REPLY
    responseEmbed = embeds.Embed(title=embedTitle, colour=embedColor)
    embedFooter = f"{result['queryresult']['timing']} second response\n1/{len(fields)}"
    responseEmbed.set_footer(text=embedFooter)
    responseEmbed.add_field(name=fields[0]['name'], value=f"```{fields[0]['value']}```")
    responseEmbed.set_image(url=images[0])
    sentTime = datetime.utcnow()
    responseEmbed.timestamp = sentTime
    await responseMessage.edit(embed=responseEmbed)
    # if there is more than one field, allow them to be switched between with arrows
    await updatePresence()
    if len(fields) > 1:
        for emoji in reactionEmojis:
            await responseMessage.add_reaction(emoji)
        activeMessages[responseMessage.id] = {"fields": fields, "images": images, "title": embedTitle, "color": embedColor, "timestamp": sentTime, "response": result['queryresult']['timing'], "index": 0}
        await removeAfterWait(responseMessage.id, ctx.message.guild if ctx.message.guild else ctx.message.author,)
        if ctx.guild: await responseMessage.clear_reactions()

# =stats - shows stats about Wumpus|Alpha
@bot.command(name='stats', help='Shows stats about Wumpus|Alpha')
async def stats(ctx):
    statsColor = embeds.Colour.from_rgb(114, 137, 218)

    with open('queryCount.log', 'r') as rf:
        totalQueries = rf.read()
    totalServers = len(bot.guilds)
    currentTime = datetime.now()
    uptime = (datetime.min + (currentTime - liveTime)).time()
    uptimeDay = int(currentTime.strftime('%d')) - int(liveTime.strftime('%d'))
    statsEmbed = embeds.Embed(title="Wumpus|Alpha stats", colour=statsColor)
    statsEmbed.timestamp = datetime.utcnow()
    statsEmbed.add_field(name="Servers", value=f"```{totalServers}```")
    statsEmbed.add_field(name="Answers", value=f"```{totalQueries}```")
    statsEmbed.add_field(name="Uptime", value=f"```{uptimeDay} d {uptime.strftime('%H h %M m %S s')}```")
    await ctx.send(embed=statsEmbed)

# =invite - DMs the user an invite link for the bot
@bot.command(name='invite', help='DMs the user an invite link for the bot')
async def invite(ctx):
    # variables
    inviteLink = "https://discord.com/oauth2/authorize?client_id=721468774699499521&permissions=75776&scope=bot"
    inviteColor = embeds.Colour.from_rgb(114, 137, 218)

    # creating and sending invite
    inviteEmbed = embeds.Embed(title="Want Wumpus|Alpha in your server? Use this link!", url=inviteLink, colour=inviteColor)
    requested = ctx.message.author
    DM = await requested.create_dm()
    await DM.send(embed=inviteEmbed)

# starting the bot
bot.run(TOKEN)