import discord, io, math, os
from PIL import Image, ImageDraw, ImageFont

from core.settings import SettingsManager
from util.embeds import TextTableEmbed, PaginatedTextTable
from util.guilds import guild_tags_from_names
from util.mappings import UI_EMOJI_MAP
from util.requests import fetch_player_busts


FONT_PATHS = [
    "MinecraftRegular.ttf",
    "assets/MinecraftRegular.ttf",
    "assets/fonts/MinecraftRegular.ttf",
]


def _resolve_font_path() -> str:
    base_dir = os.path.dirname(os.path.dirname(__file__))

    for path in FONT_PATHS:
        candidates = [path, os.path.join(base_dir, path)]
        for candidate in candidates:
            if os.path.exists(candidate):
                return candidate
    return FONT_PATHS[0]


class BoardView(discord.ui.View):
    def __init__(
        self,
        user_id,
        data: list[tuple[str, int]],
        title: str = "Leaderboard",
        max_page: int = None,
        stat_counter: str = "Value",
        is_guild_board: bool = False,
        use_text_embed: bool = True,
        show_rank: bool = True,
        headers: list[str] = None,
    ):
        super().__init__()
        self.user_id = user_id
        self.data = data
        self.max_page = max_page if max_page is not None else math.ceil(len(data) / 10)
        self.title = title
        self.show_rank = show_rank
        if headers:
            self.headers = (["Rank"] + headers) if show_rank else headers
        else:
            self.headers = ["Name", stat_counter]
            if show_rank:
                self.headers.insert(0, "Rank")

        self.stat_counter = stat_counter
        self.is_guild_board = is_guild_board
        self.use_text_embed = use_text_embed

        self.page = 0 

        setting = SettingsManager("user", user_id).get("preferred_leaderboard_output_type")
        self.is_fancy = True if setting == "image" else False


    @discord.ui.button(emoji=UI_EMOJI_MAP["left_arrow"], row=1)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page -= 1
        if self.page < 0:
            self.page = 0
            await interaction.response.send_message("You are at the first page!", ephemeral=True)
        else:
            await self.update(interaction)


    @discord.ui.button(emoji=UI_EMOJI_MAP["right_arrow"], row=1)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        if self.page > self.max_page:
            self.page = self.max_page
            await interaction.response.send_message("You are at the last page!", ephemeral=True)
        else:
            await self.update(interaction)


    async def update(self, interaction: discord.Interaction):
        await interaction.response.defer()

        if self.is_fancy:
            board = await build_board(
                self.data,
                self.page,
                is_guild_board=self.is_guild_board,
                show_rank=self.show_rank,
            )
            await interaction.edit_original_response(embed=None, view=self, attachments=[board])
        else:
            start = self.page * 10
            end = start + 10
            sliced = self.data[start:end]

            if self.show_rank:
                for i in range(len(sliced)):
                    sliced[i] = [f"{i+start+1}.", sliced[i][0], sliced[i][1]]

            if self.use_text_embed:
                embed = TextTableEmbed(self.headers, sliced, title=self.title, color=0x333333)
                await interaction.edit_original_response(embed=embed, view=self, attachments=[])
            else:
                await PaginatedTextTable.send(interaction, self.headers, self.data, "Warcount sum for guilds")



class WarcountBoardView(discord.ui.View):
    def __init__(
        self,
        user_id,
        headers,
        rows,
        listed_classes,
        is_guild_board: bool = False,
        timeout=60,
    ):
        super().__init__(timeout=timeout)
        self.listed_classes = listed_classes

        self.page = 0
        self.headers = headers
        self.data = rows
        self.user_id = user_id

        self.is_guild_board = is_guild_board

        setting = SettingsManager("user", user_id).get("preferred_leaderboard_output_type")
        self.is_fancy = True if setting == "image" else False

        self.max_pages = math.ceil(len(rows) / 10)


    async def update_message(self, interaction: discord.Interaction):
        if self.is_fancy:
            await interaction.response.defer()
            content = await build_warcount_board(self.data, self.page, self.listed_classes)
            await interaction.edit_original_response(content="", view=self, attachments=[content])
        else:
            start, end = self.page * 10, (self.page + 1) * 10
            sliced = self.data[start:end]

            widths = [len(h) for h in self.headers]
            fmt = ' ┃ '.join(f'%{w}s' for w in widths)

            lines = [fmt % tuple(self.headers)]
            separator = ''.join('╋' if c == '┃' else '━' for c in lines[0])
            lines.append(separator)

            for row in sliced:
                lines.append(' ┃ '.join(str(cell).ljust(widths[i]) for i, cell in enumerate(row)))
            lines.append(separator)

            content = '```isbl\n' + '\n'.join(lines) + '```'
            await interaction.response.edit_message(content=content, view=self, attachments=[])


    @discord.ui.button(emoji=UI_EMOJI_MAP["left_arrow"])
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
            await self.update_message(interaction)
        else:
            await interaction.response.defer()


    @discord.ui.button(emoji=UI_EMOJI_MAP["right_arrow"])
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < self.max_pages - 1:
            self.page += 1
            await self.update_message(interaction)
        else:
            await interaction.response.defer()



async def build_board(
    data: list[tuple[str, int]],
    page: int,
    is_guild_board: bool = False,
    show_rank: bool = True,
) -> discord.File:
    data_list = []
    for i in range(len(data)):
        data_list.append([i + 1, data[i][0], data[i][1]])

    rank_margin = 45
    model_margin = 115 if show_rank else 45
    name_margin = 205 if show_rank else 135
    value_margin = 685

    font = ImageFont.truetype(_resolve_font_path(), 20)

    board = Image.new("RGBA", (730, 695), (110, 110, 110))

    overlay = Image.open("assets/board_segment.png")
    overlay2 = Image.open("assets/board_segment_dark.png")
    overlay_toggle = True

    draw = ImageDraw.Draw(board)

    names = []
    for i in data_list:
        names.append(i[1])

    if is_guild_board:
        tags = (await guild_tags_from_names(names))[0]
    else:
        await fetch_player_busts(names)

    for i in range(1, 11):
        try:
            stat = data_list[(i - 1) + (page * 10)]
        except IndexError:
            continue

        height = ((i - 1) * 69) + 5

        board.paste(overlay if overlay_toggle else overlay2, (5, height), overlay)
        overlay_toggle = not overlay_toggle

        if is_guild_board:
            tag = tags[names.index(stat[1])]
            try:
                model_img = Image.open(f"assets/icons/guilds/{tag}.png", 'r').convert("RGBA")
            except FileNotFoundError:
                model_img = Image.new("RGBA", (64, 64))
        else:
            try:
                model_img = Image.open(f"/tmp/{stat[1]}_model.png", 'r').convert("RGBA")
            except Exception as e:
                model_img = Image.open(f"assets/unknown_model.png", 'r').convert("RGBA")
                print(f"Error loading image: {e}")

        model_img = model_img.resize((64, 64))
        board.paste(model_img, (model_margin, height), model_img.getchannel("A"))

        if show_rank:
            draw.text((rank_margin, height + 22), "#" + str(stat[0]), font=font)
        draw.text((name_margin, height + 22), str(stat[1]), font=font)
        draw.text((value_margin, height + 22), str(stat[2]), font=font, anchor="rt")

    with io.BytesIO() as img_binary:
        board.save(img_binary, 'PNG')
        img_binary.seek(0)
        file = discord.File(fp=img_binary, filename="board.png")

    return file


async def build_warcount_board(
    data: list[tuple],
    page: int,
    listed_classes: list[str],
    is_guild_board: bool = False,
) -> discord.File:
    start = page * 10
    end = start + 10
    sliced = data[start:end]

    img = Image.open("assets/warcount_template.png")
    draw = ImageDraw.Draw(img)

    name_fontsize = 20
    text_fontsize = 16
    total_fontsize = 18

    font_path = _resolve_font_path()
    name_font = ImageFont.truetype(font_path, name_fontsize)
    text_font = ImageFont.truetype(font_path, text_fontsize)
    total_font = ImageFont.truetype(font_path, total_fontsize)

    names = []
    for i in sliced:
        names.append(i[1])

    if is_guild_board:
        tags = (await guild_tags_from_names(names))[0]
    else:
        await fetch_player_busts(names)

    i = 1
    for row in sliced:
        y = ((57 * (i / 2)) + (59 * (i / 2))) + 27

        draw.text((62, y), f"{row[0]}.", "white", total_font, anchor="rm")
        draw.text((153, y), row[1], "white", name_font, anchor="lm")

        if is_guild_board:
            tag = tags[names.index(row[1])]
            try:
                model_img = Image.open(f"assets/icons/guilds/{tag}.png", 'r').convert("RGBA")
                model_img = model_img.crop(model_img.getbbox())
            except FileNotFoundError:
                model_img = Image.new("RGBA", (54, 54))
        else:
            try:
                model_img = Image.open(f"/tmp/{row[1]}_model.png", 'r').convert("RGBA")
            except Exception as e:
                model_img = Image.open(f"assets/unknown_model.png", 'r').convert("RGBA")
                print(f"Error loading image: {e}")

        model_img = model_img.resize((54, 54))
        img.paste(model_img, (84, int(y) - 29), model_img.getchannel("A"))

        draw.text((445, y), row[2], "white", total_font, anchor="mm")

        x = 0  # Offset for class warcount columns

        if "ARCHER" in listed_classes:
            draw.text((532, y), str(row[3 + x]), "white", text_font, anchor="mm")
            x += 1
        if "WARRIOR" in listed_classes:
            draw.text((593, y), str(row[3 + x]), "white", text_font, anchor="mm")
            x += 1
        if "MAGE" in listed_classes:
            draw.text((658, y), str(row[3 + x]), "white", text_font, anchor="mm")
            x += 1
        if "ASSASSIN" in listed_classes:
            draw.text((718, y), str(row[3 + x]), "white", text_font, anchor="mm")
            x += 1
        if "SHAMAN" in listed_classes:
            draw.text((780, y), str(row[3 + x]), "white", text_font, anchor="mm")
            x += 1

        draw.text((827, y), str(row[3 + x]), "white", total_font, anchor="lm")

        i += 1

    img_binary = io.BytesIO()
    img.save(img_binary, 'PNG')
    img_binary.seek(0)

    return discord.File(fp=img_binary, filename="board.png")
