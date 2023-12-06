
import logging
from autocorrect import Speller

class Correcter:
    _spell = None
    _quick_spell = None

    @staticmethod
    def load():
        if not isinstance(Correcter._spell, Speller):
            Correcter._spell = Speller(lang='en', fast=False)
        if not isinstance(Correcter._quick_spell, Speller):
            Correcter._quick_spell = Speller(lang='en', fast=True)

    @staticmethod
    def slow_correct(string:str):
        corrected = Correcter._spell(string)
        if string != corrected:
            logging.debug(f"Spelling errors detected in: {string}, corrected to {corrected}")
        return corrected

    @staticmethod
    def quick_correct(string:str):
        corrected = Correcter._quick_spell(string)
        if string != corrected:
            logging.debug(f"Spelling errors detected in: {string}, corrected to {corrected}")
        return corrected