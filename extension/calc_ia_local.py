# -*- coding: utf-8 -*-
"""Point d'entrée de l'extension : ouvre l'assistant depuis le menu « IA locale »."""
import traceback
import unohelper
from com.sun.star.task import XJobExecutor

IMPL = "fr.fredericdol.calcialocale.Launcher"


class Launcher(unohelper.Base, XJobExecutor):
    def __init__(self, ctx):
        self.ctx = ctx

    def trigger(self, args):
        try:
            from calc_ia.dialog import open_assistant
            open_assistant(self.ctx)
        except Exception:
            traceback.print_exc()


g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationHelper.addImplementation(Launcher, IMPL, ("com.sun.star.task.Job",))
