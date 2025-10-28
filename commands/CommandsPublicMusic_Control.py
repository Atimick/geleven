# CommandsPublicMusic_Control.py
import discord
from .CommandsPublicMusic_Queue import MusicQueue

class MusicControlView(discord.ui.View):
    # THAY ĐỔI: Nhận thêm music_queue instance
    def __init__(self, vc: discord.VoiceClient, music_queue: MusicQueue):
        super().__init__(timeout=None)
        self.vc = vc
        self.music_queue = music_queue # LƯU TRỮ queue

    @discord.ui.button(label="⏯️ Pause", style=discord.ButtonStyle.gray)
    async def pause_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Logic này chỉ cần thao tác trên voice client là đủ
        if self.vc.is_playing():
            self.vc.pause()
            button.label = "▶️ Resume"
            await interaction.response.edit_message(view=self)
            await interaction.followup.send("⏸️ Đã tạm dừng.", ephemeral=True)
        elif self.vc.is_paused():
            self.vc.resume()
            button.label = "⏯️ Pause"
            await interaction.response.edit_message(view=self)
            await interaction.followup.send("▶️ Tiếp tục phát.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Không có gì để tạm dừng/tiếp tục.", ephemeral=True)


    @discord.ui.button(label="⏹️ Stop", style=discord.ButtonStyle.red)
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # THAY ĐỔI QUAN TRỌNG: Gọi music_queue.stop() để dừng phát, xoá hàng đợi, và ngắt kết nối an toàn
        if self.vc and self.vc.is_connected():
            await self.music_queue.stop() 
            await interaction.response.send_message("⛔ Bot đã dừng, rời voice và xóa hàng đợi.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Bot không ở voice channel nào.", ephemeral=True)