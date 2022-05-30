import discord
from discord import Interaction
from discord.ui import (
    Button,
    Modal,
    TextInput,
    View,
    button
)


__all__ = [
    'ListMenu'
]


class PageModal(Modal):
    """Modal sent when clicking Page button in ListMenu."""

    def __init__(self, menu, title='Change page') -> None:
        super().__init__(title=title)
        self.page: TextInput = TextInput(
            label=f'Page number | from 1 to {menu.max_pages}',
            style=discord.TextStyle.short
        )
        self.add_item(self.page)
        self.menu = menu

    async def on_submit(self, interaction: Interaction) -> None:
        if self.page.value is None:
            raise TypeError('Page is not set')
        await self.menu.edit(interaction, page=int(self.page.value) - 1)


class ListMenu(View):
    """
    An embed description-based list display with page changing through modals.

    The text displayed is gathered through the items' str implementations.

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
    """

    def __init__(
        self,
        items: list[str],
        owner: discord.Member,
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
        self.owner = owner
        self._basic_desc = description + ' \n\n '
        self._per_page = per_page
        self._page = -1

    @property
    def max_pages(self) -> int:
        """Max pages of the menu."""
        pages, mod = divmod(len(self._items), self._per_page)
        return pages + 1 if mod else pages

    @property
    def page(self) -> int:
        """Page number."""
        return self._page

    def _update_page(self, page: int):
        self._page = page
        items = map(
            str, self._items[page*self._per_page: (page + 1) * self._per_page])
        self._embed.description = self._basic_desc + '\n'.join(items)
        self._embed.set_footer(text=f'{self._page + 1}/{self.max_pages}')

    async def edit(self, interaction: Interaction, *, page: int) -> None:
        """Edit the menu's page and the discord embed."""
        page = min(max(0, page), self.max_pages - 1)
        self._update_page(page)
        await interaction.response.edit_message(embed=self._embed)

    async def start(self, interaction: Interaction) -> None:
        """Start the view."""
        if interaction.response.is_done():
            raise RuntimeError('Menu can only be started once')
        self._update_page(0)
        await interaction.response.send_message(embed=self._embed, view=self)

    async def interaction_check(self, interaction: Interaction) -> bool:
        """Fails if menu owner and interaction user are different."""
        if interaction.user == self.owner:
            return True
        await interaction.response.send_message(
            'Only the person who sent the queue command can control it',
            ephemeral=True
        )

    @button(label='«')
    async def _first_page(
        self,
        interaction: Interaction,
        button: Button
    ) -> None:
        await self.edit(interaction, page=0)

    @button(label='‹')
    async def _previous_page(
        self,
        interaction: Interaction,
        button: Button
    ) -> None:
        await self.edit(interaction, page=self._page - 1)

    @button(label='Page')
    async def _change_page(
        self,
        interaction: Interaction,
        button: Button
    ) -> None:
        await interaction.response.send_modal(PageModal(self))

    @button(label='›')
    async def _next_page(
        self,
        interaction: Interaction,
        button: Button
    ) -> None:
        await self.edit(interaction, page=self._page + 1)

    @button(label='»')
    async def _last_page(
        self,
        interaction: Interaction,
        button: Button
    ) -> None:
        await self.edit(interaction, page=self.max_pages - 1)
