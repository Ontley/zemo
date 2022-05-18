import discord
from discord.ui import (
    button,
    Button,
    Modal,
    TextInput,
    View
)


__all__ = [
    'ListMenu'
]


class PageModal(Modal):
    def __init__(self, menu, title='Change page') -> None:
        super().__init__(title=title)
        self.page: TextInput = TextInput(
            label=f'Page number | from 1 to {menu.max_pages}', style=discord.TextStyle.short)
        self.add_item(self.page)
        self.menu = menu

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if self.page.value is None:
            raise TypeError('Page is not set')
        await self.menu.edit(interaction, page=int(self.page.value) - 1)


class ListMenu(View):
    '''
    An embed description-based list display with page changing through modals

    The text displayed is gathered through the items' str implementations

    ----------
    Attributes
    ----------
    items: `Iterable[T]`
        An iterable of items to display
    title: `str`
        The title of the embed
    description: `str`
        The description of the menu (excluding the items)
    per_page: `Optional[int]`
        The amount of items to display per page
    timeout: `Optional[float]`
        See `discord.ui.View.timeout`
    '''

    def __init__(
        self,
        items: list[str],
        *,
        title: str,
        description: str,
        per_page: int = 15,
        timeout: float = 180
    ) -> None:
        super().__init__(timeout=timeout)
        self._embed = discord.Embed(
            title=title,
            description=description
        )
        self._items = items
        self._basic_desc = description + ' \n\n '
        self._per_page = per_page
        self._page = -1

    @property
    def max_pages(self) -> int:
        pages, mod = divmod(len(self._items), self._per_page)
        return pages + 1 if mod else pages

    @property
    def page(self) -> int:
        return self._page

    @page.setter
    def page(self, page: int):
        self._page = min(max(0, page), self.max_pages)
        items = map(
            str, self._items[page*self._per_page: (page + 1) * self._per_page])
        self._embed.description = self._basic_desc + '\n'.join(items)
        self._embed.set_footer(text=f'{self._page + 1}/{self.max_pages}')

    async def edit(self, interaction: discord.Interaction, *, page: int) -> None:
        self.page = min(max(0, page), self.max_pages - 1)
        await interaction.response.edit_message(embed=self._embed)

    async def start(self, interaction: discord.Interaction) -> None:
        self._interaction = interaction
        if interaction.response.is_done():
            raise RuntimeError('Menu was already started')
        self.page = 0
        await interaction.response.send_message(embed=self._embed, view=self)

    @button(label='«')
    async def _first_page(self, interaction, button) -> None:
        await self.edit(interaction, page=0)

    @button(label='‹')
    async def _previous_page(self, interaction, button) -> None:
        await self.edit(interaction, page=self._page - 1)

    @button(label='Page')
    async def _change_page(self, interaction: discord.Interaction, button: Button) -> None:
        await interaction.response.send_modal(PageModal(self))

    @button(label='›')
    async def _next_page(self, interaction, button) -> None:
        await self.edit(interaction, page=self._page + 1)

    @button(label='»')
    async def _last_page(self, interaction, button) -> None:
        await self.edit(interaction, page=self.max_pages - 1)
