# -*- coding: utf-8 -*-
"""
/***************************************************************************
 OSMPlugin
                                 A QGIS plugin
 Extrai interseção e diferenças geométricas e nominais
                             -------------------
        begin                : 2018-06-05
        copyright            : (C) 2018 by IBGE
        email                : andre.censitario@ibge.gov.br
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load OSMPlugin class from file OSMPlugin.

    :param iface: A QGIS interface instance.
    :type iface: QgisInterface
    """
    #
    from .osm_plugin import OSMPlugin
    return OSMPlugin(iface)
