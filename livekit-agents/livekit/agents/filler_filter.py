# livekit/agents/filler_filter.py

class FillerFilter:
    def __init__(self, ignored_words=['uh', 'umm', 'hmm', 'haan']):
        self.ignored_words = set(ignored_words)
        self.agent_speaking = False
    
    def is_filler_only(self, transcript: str) -> bool:
        words = transcript.lower().strip().split()
        return all(word in self.ignored_words for word in words)
    
    def should_ignore_interruption(self, transcript: str) -> bool:
        return self.agent_speaking and self.is_filler_only(transcript)
