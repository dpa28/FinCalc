from kivymd.uix.list import TwoLineAvatarIconListItem, IconLeftWidget
from kivy.uix.image import AsyncImage

class CryptoListItem(TwoLineAvatarIconListItem):
    def __init__(self, **kwargs):
        self.image_source = kwargs.pop('image_source', None)
        self.coin_data = kwargs.pop('coin_data', None)
        super().__init__(**kwargs)
        if self.image_source:
            img = AsyncImage(source=self.image_source, size_hint=(None, None), size=("40dp", "40dp"))
            container = IconLeftWidget()
            container.add_widget(img)
            self.add_widget(container)