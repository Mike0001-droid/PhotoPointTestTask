class ProviderRegistry:
    def __init__(self):
        self._providers = {}
    
    def register(self, channel: str, provider):
        self._providers[channel] = provider
    
    def get_provider(self, channel: str):
        return self._providers.get(channel)
    
    def get_available_channels(self):
        return list(self._providers.keys())