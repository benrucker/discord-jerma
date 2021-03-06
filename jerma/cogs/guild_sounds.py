import asyncio
from colorama import Fore as t
from colorama import Style
import discord
from discord.embeds import Embed
from discord.ext import commands
from .control import JoinFailedError
from glob import glob
import random
import os
import time


# will move these up to a broader scope later
YES = ['yes','yeah','yep','yeppers','of course','ye','y','ya','yah']
NO  = ['no','n','nope','start over','nada', 'nah']

y = t.YELLOW + Style.BRIGHT
c = t.CYAN + Style.NORMAL


async def manage_sounds_check(ctx):
    p = ctx.channel.permissions_for(ctx.author)
    return p.kick_members or \
           p.ban_members or \
           p.administrator or \
           p.manage_guild or \
           p.move_members or \
           p.manage_nicknames or \
           p.manage_roles or \
           p.deafen_members or \
           p.mute_members or \
           p.mute_members


def setup(bot):
    bot.add_cog(GuildSounds(bot))


class GuildSoundsError(commands.CommandError):
    def __init__(self, error, msg):
        self.error = error
        self.msg = msg


class GuildSounds(commands.Cog):
    """Cog for maintaining guild-specific sound functionality."""

    def __init__(self, bot):
        self.bot = bot
        #self.path_to_guilds = path_to_guilds
        #self.sounds_dict  # keep this static until add,rm,or rename

    async def cog_command_error(self, ctx, error):
        if isinstance(error, GuildSoundsError):
            print(error.error)
            await ctx.send(error.msg)
        elif isinstance(error, JoinFailedError):
            await ctx.send(error)

    def get_sound(self, sound, guild: discord.Guild):
        ginfo = self.bot.get_guildinfo(guild.id)
        sounds = self.make_sounds_dict(guild.id)
        try:
            return os.path.join(ginfo.sound_folder, sounds[sound.lower()])
        except KeyError:
            return None

    def get_random_sound(self, guild: discord.Guild):
        ginfo = self.bot.get_guildinfo(guild.id)
        sounds = self.make_sounds_dict(guild.id)
        return os.path.join(ginfo.sound_folder, random.choice(list(sounds.values())))

    def has_sound_file(self, message):
        if len(message.attachments) == 0:
            return False
        attachment = message.attachments[0]
        return attachment.filename.endswith('.mp3') or attachment.filename.endswith('.wav')

    def get_guild_sound_path(self, guild):
        if type(guild) is discord.Guild:
            ginfo = self.bot.get_guildinfo(guild.id)
        else:
            ginfo = self.bot.get_guildinfo(guild)
        return ginfo.sound_folder

    async def add_sound_to_guild(self, sound, guild, filename=None):
        folder = self.get_guild_sound_path(guild)
        if not filename:
            filename = sound.filename.lower()
        path = os.path.join(folder, filename)
        await sound.save(path)

    @commands.command(aliases=['add'])
    @commands.check(manage_sounds_check)
    async def addsound(self, ctx, *args):
        """Add a sound to the sounds list. Requires certain server perms."""
        arg = ' '.join(args).lower()

        # get sound file from user
        await ctx.send('Alright gamer, send the new sound.')

        def check(message):
            return message.author is ctx.author and self.has_sound_file(message)
        message = await self.bot.wait_for('message', timeout=20, check=check)

        # construct name from arg or attachment
        if arg:
            if arg.endswith(('.mp3', '.wav')):
                filename = arg
            else:
                filename = arg + '.' + message.attachments[0].filename.split('.')[-1]
        else:
            filename = message.attachments[0].filename
        filename = filename.lower()

        # remove old sound if there
        name = filename.split('.')[0].lower()
        existing = self.get_sound(name, ctx.guild)
        if existing:
            await ctx.send(f'There\'s already a sound called _{name}_, bucko. Sure you want to replace it? (yeah/nah)')

            def check2(message):
                return message.author is ctx.author
            replace_msg = await self.bot.wait_for('message', timeout=20, check=check2)
            if replace_msg.content.lower().strip() in YES:
                self.delete_sound(os.path.split(existing)[1], ctx.guild)
            else:
                await ctx.send('Yeah, I like the old one better too.')
                return

        await self.add_sound_to_guild(message.attachments[0], ctx.guild, filename=filename)
        await ctx.send('Sound added, gamer.')

    def delete_sound(self, filepath, guild: discord.Guild):
        path = self.bot.get_guildinfo(guild.id).sound_folder
        if 'sounds' not in filepath:
            filepath = os.path.join(path, filepath)
        print('deleting ' + filepath)
        os.remove(filepath)

    @commands.command(aliases=['removesound'])
    @commands.check(manage_sounds_check)
    async def remove(self, ctx, *args):
        """Remove a sound clip."""
        if not args:
            raise GuildSoundsError('No sound specified in remove command.',
                                'Gamer, you gotta tell me which sound to remove.')

        sound_name = ' '.join(args)
        sound = self.get_sound(sound_name, ctx.guild)

        if not sound:
            raise GuildSoundsError('Sound ' + sound + ' not found.',
                                'Hey gamer, that sound doesn\'t exist.')

        self.delete_sound(sound, ctx.guild)
        await ctx.send('The sound has been eliminated, gamer.')

    def rename_file(self, old_filepath, new_filepath):
        os.rename(old_filepath, new_filepath)

    @commands.command(aliases=['renamesound'])
    @commands.check(manage_sounds_check)
    async def rename(self, ctx, *args):
        """Rename a sound clip."""
        if not args:
            raise GuildSoundsError('No sound specified in rename command.',
                                'Yo gamer, do it like this: `$rename old name, new name`')

        old, new = ' '.join(args).split(', ')
        print(f'renaming {old} to {new} in {ctx.guild.name}')
        old_filename = self.get_sound(old, ctx.guild)
        if old_filename:
            new_filename = old_filename[:33] + new.lower() + old_filename[-4:]
            try:
                self.rename_file(old_filename, new_filename)
                await ctx.send('Knuckles: cracked. Headset: on. **Sound: renamed.**\nYup, it\'s Rats Movie time.')
            except Exception as e:
                raise GuildSoundsError(f'Error {type(e)} while renaming sound',
                                    'Something went wrong, zoomer. Make sure no other sound has the new name, okay?')
        else:
            await ctx.send(f'I couldn\'t find a sound with the name {old}, aight?')

    def make_sounds_dict(self, id):
        sounds = {}
        sound_folder = os.path.join(self.bot.path, self.get_guild_sound_path(id))
        #print('Finding sounds in:', sound_folder)
        for filepath in glob(os.path.join(sound_folder, '*')): # find all files in folder w/ wildcard
            filename = os.path.basename(filepath)
            extension = filename.rsplit('.', 1)[1]
            if extension not in ['mp3', 'wav']:
                continue
            sounds[filename.rsplit('.', 1)[0]] = filename
        return sounds

    def get_list_embed(self, guild_info):
        # this was rewritten unextensibly but whatever
        _lim = 1024
        sounds = '\n'.join(sorted(self.make_sounds_dict(guild_info.id)))
        overflow = None
        if len(sounds) > _lim:
            _split = sounds.rindex('\n', 0, len(sounds) // 2)
            overflow = sounds[_split:]
            sounds = sounds[:_split]
        sound_embed = Embed(title=" list | all of the sounds you can play through Jerma", description="`$play <sound>` to play them in your server, gamer!", color=0x66c3cb)
        # soundEmbed.set_author(name="Jermabot Help", url="https://www.youtube.com/watch?v=fnbvTOcNFhU")#, icon_url="attachment://avatar.png")
        # soundEmbed.set_thumbnail(url="attachment://thumbnail.png")
        sound_embed.add_field(name='Sounds?', value=sounds, inline=True)
        if overflow:
            sound_embed.add_field(name='Sounds!', value=overflow, inline=True)
        sound_embed.set_footer(text="Message your server owner to get custom sounds added!")

        return sound_embed

    @commands.command(name='list', aliases=['sounds'])
    async def _list(self, ctx):
        """Send the user a list of sounds that can be played."""
        ginfo = self.bot.get_guildinfo(ctx.guild.id)
        # avatar = discord.File(os.path.join('resources', 'images', 'avatar.png'), filename='avatar.png')
        # thumbnail = discord.File(os.path.join('resources', 'images', 'avatar.png'), filename='thumbnail.png')
        await ctx.author.send(embed=self.get_list_embed(ginfo),
                              #files=[avatar, thumbnail],
                              )
        await ctx.message.add_reaction("✉")

    @commands.command()
    async def play(self, ctx, *args):
        """Play a sound."""
        if not args:
            raise GuildSoundsError('No sound specified in play command.',
                                'Gamer, you gotta tell me which sound to play.')

        sound = ' '.join(args)
        current_sound = self.get_sound(sound, ctx.guild)
        if not current_sound:
            raise GuildSoundsError('Sound ' + sound + ' not found.',
                                'Hey gamer, that sound doesn\'t exist.')

        control = self.bot.get_cog('Control')
        print('connecting to user...')
        vc = await control.connect_to_user(ctx)
        print('should be connected')
        self.bot.get_cog('SoundPlayer').play_sound_file(current_sound, vc)
        print('dispatched sound_file_play')

    @commands.command()
    async def random(self, ctx):
        sound = self.get_random_sound(ctx.guild)
        if not sound:
            raise GuildSoundsError('Guild has no sounds.',
                'Sorry gamer, but you need to add some sounds for me to play!')

        control = self.bot.get_cog('Control')
        vc = await control.connect_to_user(ctx)
        self.bot.get_cog('SoundPlayer').play_sound_file(sound, vc)

    @commands.command(aliases=['sleep'])
    async def snooze(self, ctx):
        """Disable join sounds for 4 hours or until you call snooze again."""
        r = self.bot.get_guildinfo(ctx.guild.id).toggle_snooze()
        if r:
            # set nick to JermaSnore
            t = time.localtime(r)
            await ctx.me.edit(nick='JermaSnore')
            await ctx.send(f'Snoozed until {t.tm_hour % 12}:{t.tm_min:02} {t.tm_zone}. See you then, champ!')
        else:
            # set nick to JermaBot
            await ctx.me.edit(nick=None)
            await ctx.send(f'**I HAVE AWOKEN**')

    def get_muted_sound(self):
        return os.path.join('resources', 'soundclips', 'muted.mp3')

    def get_yoni_leave_sound(self):
        sound = os.path.join('resources', 'soundclips', 'workhereisdone.wav')
        return sound

    def voice_state_diff_str(self, v1, v2) -> str:
        """Return a descriptive string of differences between two voice states."""
        out = ''
        for x, y in zip(repr(v1).split(' '), repr(v2).split(' ')):
            if x != y:
                out += '\tfrom ' + x + ' to ' + y + '\n'
        return out[:-1]

    def user_joined_channel(self, before, after):
        joined_voice = not before.channel and after.channel
        moved_chan = (before.channel and after.channel) and before.channel != after.channel
        return joined_voice or moved_chan

    async def play_join_sound(self, member, vc):
        print(f'{y}Checking if {member.voice.channel} has a user limit...')
        print(member.voice.channel.user_limit)
        if member.voice.channel.user_limit:
            return

        print(f'{y}Playing join sound if exists...')
        join_sound = self.get_sound(member.name, member.guild)
        if join_sound:
            print(f'{y}Found join sound')
            vc = await self.bot.get_cog('Control').connect_to_channel(vc, member.voice.channel)
            print(f'{y}{vc}')
            if not vc:
                return
            self.bot.get_cog('SoundPlayer').play_sound_file(join_sound, vc)
        else:
            print('No join sound for user')

    def old_voice_channel_has_no_people(self, vc):
        return len([x for x in vc.channel.members if not x.bot]) == 0

    async def disconnect_from_voice(self, vc):
        print(f'[{time.ctime()}] {y}Disconnecting from {c}{vc.guild} #{vc.channel} {y}because it is empty.')
        await vc.disconnect()

    def was_user_server_muted(self, before, after):
        return (not before.mute) and after.mute 

    def play_muted(self, vc):
        sound = self.get_muted_sound()
        if sound:
            self.bot.get_cog('SoundPlayer').play_sound_file(sound, vc)

    def user_left_channel(self, before, after):
        was_in_vc = before != None
        not_in_vc = not after or not hasattr(after, 'channel') or not after.channel
        return was_in_vc and not_in_vc

    def play_leave_sound(self, member, vc):
        leave_sound = self.get_yoni_leave_sound()
        if leave_sound and member.id in [196742230659170304]:
            self.bot.get_cog('SoundPlayer').play_sound_file(leave_sound, vc)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """
        Manage functionality when someone changes voice state.

        Play a join noise when a user joins a channel,
        cleanup if kicked from voice,
        play a leave sound for a certain user,
        or disconnect if connected to an empty voice channel.
        """
        # member (Member) – The member whose voice states changed.
        # before (VoiceState) – The voice state prior to the changes.
        # after (VoiceState) – The voice state after the changes.
        print(f'[{time.ctime()}] Voice state update: {member.name}\n{self.voice_state_diff_str(before, after)}')

        old_vc = self.bot.get_cog('Control').get_existing_voice_client(member.guild)
        g = self.bot.get_guildinfo(member.guild.id)

        # don't play join sound if conditional
        if g.is_snapping or g.is_snoozed():
            print(f'{y}Ignoring voice state update due to snap or snooze')
            return
        else:
            target_nick = "JermaBot"
            if member.guild.me.display_name != target_nick:
                print(f'{y}Reset nickname in {member.guild}')
                await member.guild.me.edit(nick=target_nick)

        # cleanup connection if kicked
        if member.id == self.bot.user.id:
            print(f'{y}Voice update was self')
            if old_vc and not after.channel:
                print('Attempting to disconnect from old voice client')
                await old_vc.disconnect()
            return
        
        if self.user_joined_channel(before, after):
            await self.play_join_sound(member, old_vc)
        elif old_vc and self.old_voice_channel_has_no_people(old_vc):
            await self.disconnect_from_voice(old_vc)
        elif old_vc and self.user_left_channel(before, after) and before.channel == old_vc.channel:
            self.play_leave_sound(member, old_vc)
        elif old_vc and self.was_user_server_muted(before, after) and before.channel == old_vc.channel:
            self.play_muted(old_vc)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """Initialize guild sounds directory for new guild."""
        os.makedirs(os.path.join('guilds', f'{guild.id}', 'sounds'), exist_ok=True)
        self.bot.make_guildinfo(guild)
        print(f'Added to {guild.name}:{guild.id}!')
