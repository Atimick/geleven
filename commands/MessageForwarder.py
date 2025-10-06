import discord
from discord.ext import commands

# --- Config ---
FORWARD_CHANNELS = {
    1390257227520151583: 1390257273237934192,  # BloodyHand → VRXD
    1390257273237934192: 1390257227520151583   # VRXD → BloodyHand
}

OBSERVED_SOURCE_ID = 1363682161030332647
OBSERVE_CHANNEL_ID = 1393168885464698971


class MessageForwarder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        origin_channel = message.channel.id

        # 1. Forward 2 chiều
        target_channel_id = FORWARD_CHANNELS.get(origin_channel)
        if target_channel_id:
            target_channel = self.bot.get_channel(target_channel_id)
            if target_channel:
                await self._forward_to_channel(message, target_channel)

        # 2. Forward một chiều → kênh log
        if origin_channel == OBSERVED_SOURCE_ID:
            observe_channel = self.bot.get_channel(OBSERVE_CHANNEL_ID)
            if observe_channel:
                await self._forward_to_channel(message, observe_channel)
                
    async def _forward_to_channel(self, message: discord.Message, target_channel: discord.TextChannel):
        embed = discord.Embed(
            description=message.content or "[Không có nội dung]",
            color=discord.Color.orange(),
            timestamp=message.created_at
        )
        embed.set_author(
            name=message.author.display_name,
            icon_url=message.author.avatar.url if message.author.avatar else None
        )
        embed.set_footer(
            text=f"Từ server: {message.guild.name} • {message.created_at.strftime('%d/%m/%Y %H:%M:%S')}"
        )

        # Gắn ảnh đầu tiên (nếu có)
        image_set = False
        for attachment in message.attachments:
            if attachment.filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                embed.set_image(url=attachment.url)
                image_set = True
                break

        await target_channel.send(embed=embed)

        # Gửi các file còn lại
        for attachment in message.attachments:
            is_image = attachment.filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))
            if is_image and image_set and attachment.url == embed.image.url:
                continue
            try:
                await target_channel.send(file=await attachment.to_file())
            except Exception as e:
                print(f"❌ Lỗi khi gửi tệp đính kèm: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(MessageForwarder(bot))
