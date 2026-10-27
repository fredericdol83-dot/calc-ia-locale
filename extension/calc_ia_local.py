# -*- coding: utf-8 -*-
"""Points d'entrée de l'extension : menu « IA locale » et panneau de la barre latérale."""
import traceback

import uno
import unohelper
from com.sun.star.task import XJobExecutor
from com.sun.star.ui import XUIElementFactory, XUIElement, XToolPanel, XSidebarPanel

LAUNCHER = "fr.fredericdol.calcialocale.Launcher"
FACTORY = "fr.fredericdol.calcialocale.PanelFactory"


class Launcher(unohelper.Base, XJobExecutor):
    def __init__(self, ctx):
        self.ctx = ctx

    def trigger(self, args):
        try:
            from calc_ia.panel import open_sidebar
            open_sidebar(self.ctx)
        except Exception:
            traceback.print_exc()
            try:  # repli : la fenêtre classique
                from calc_ia.dialog import open_assistant
                open_assistant(self.ctx)
            except Exception:
                traceback.print_exc()


class PanelElement(unohelper.Base, XUIElement, XToolPanel, XSidebarPanel):
    def __init__(self, ctx, frame, parent, url):
        from calc_ia.panel import AssistantPanel
        self.Frame = frame
        self.ResourceURL = url
        self.Type = uno.getConstantByName("com.sun.star.ui.UIElementType.TOOLPANEL")
        self.panel = AssistantPanel(ctx, frame, parent)
        self.Window = self.panel.window

    # XUIElement
    def getRealInterface(self):
        return self

    def getFrame(self):
        return self.Frame

    def getResourceURL(self):
        return self.ResourceURL

    def getType(self):
        return self.Type

    # XToolPanel
    def getWindow(self):
        return self.Window

    def createAccessible(self, parent_accessible):
        return self.Window.getAccessibleContext() if hasattr(self.Window, "getAccessibleContext") else parent_accessible

    # XSidebarPanel
    def getHeightForWidth(self, width):
        h = self.panel.height_px
        return uno.createUnoStruct("com.sun.star.ui.LayoutSize", h, h, h)

    def getMinimalWidth(self):
        return 280


class PanelFactory(unohelper.Base, XUIElementFactory):
    def __init__(self, ctx):
        self.ctx = ctx

    def createUIElement(self, url, args):
        try:
            d = {a.Name: a.Value for a in args}
            return PanelElement(self.ctx, d.get("Frame"), d.get("ParentWindow"), url)
        except Exception:
            traceback.print_exc()
            raise


g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationHelper.addImplementation(Launcher, LAUNCHER, ("com.sun.star.task.Job",))
g_ImplementationHelper.addImplementation(PanelFactory, FACTORY, ("com.sun.star.ui.UIElementFactory",))
