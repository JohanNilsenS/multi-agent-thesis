"""BaseAgent är en abstrakt basklass för alla agenter i systemet.

Denna klass definierar grundläggande funktionalitet som alla agenter behöver,
inklusive loggning, initialisering och grundläggande uppgiftshantering.
"""

from typing import Optional
from ..llm_client import LLMClient

class BaseAgent:
    """En abstrakt basklass för alla agenter i systemet.
    
    Denna klass fungerar som en mall för alla agenter och definierar:
    - Grundläggande loggning
    - Initialisering med LLM-klient
    - Metoder för att avgöra om en agent kan hantera en uppgift
    - Metoder för att hantera uppgifter
    
    Attribut:
        llm (LLMClient): En instans av LLM-klienten för AI-kommunikation
        debug (bool): Om True, loggas debug-information
    """
    
    def __init__(self, llm: LLMClient, debug: bool = True):
        """Initierar en ny agent.
        
        Args:
            llm (LLMClient): En instans av LLM-klienten
            debug (bool, optional): Om True, aktiveras debug-loggning. Default är True.
        """
        self.llm = llm
        self.debug = debug

    def log(self, message: str) -> None:
        """Loggar ett meddelande om debug är aktiverat.
        
        Args:
            message (str): Meddelandet att logga
        """
        if self.debug:
            print(f"[{self.__class__.__name__}] {message}")

    async def initialize(self) -> None:
        """Initierar agenten.
        
        Denna metod bör överskrivas av subklasser för att implementera
        specifik initialiseringslogik.
        """
        pass

    def can_handle(self, task: str) -> bool:
        """Avgör om agenten kan hantera en given uppgift.
        
        Denna metod bör överskrivas av subklasser för att implementera
        specifik logik för att avgöra om en uppgift kan hanteras.
        
        Args:
            task (str): Uppgiften att utvärdera
            
        Returns:
            bool: True om agenten kan hantera uppgiften, annars False
        """
        return False

    async def handle(self, task: str) -> str:
        """Hanterar en uppgift.
        
        Denna metod bör överskrivas av subklasser för att implementera
        specifik hanteringslogik.
        
        Args:
            task (str): Uppgiften att hantera
            
        Returns:
            str: Resultatet av uppgiftshanteringen
        """
        return "Denna agent kan inte hantera denna typ av uppgift." 