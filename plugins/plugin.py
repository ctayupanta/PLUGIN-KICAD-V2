import os
import wx
import pcbnew
import csv

class PluginDemo(pcbnew.ActionPlugin):
    def __init__(self):
        super().__init__()
        self.name = "Plugin Kicad Demo"
        self.category = "Fabricación"
        self.description = "Exporta archivos para fabricación (Gerber, BOM, XY)"
        
        # Configuración de iconos (como PCBWay)
        self.pcbnew_icon_support = hasattr(self, "show_toolbar_button")
        self.show_toolbar_button = True
        self.icon_file_name = os.path.join(os.path.dirname(__file__), 'icon.png')
        self.dark_icon_file_name = os.path.join(os.path.dirname(__file__), 'icon.png')

    def Run(self):
        try:
            board = pcbnew.GetBoard()
            project_path = os.path.dirname(board.GetFileName())
            export_dir = os.path.join(project_path, "Fabricacion_PCB")
            os.makedirs(export_dir, exist_ok=True)

            # 1. Exportar Gerbers
            exported_gerbers = self._export_gerbers(board, export_dir)
            
            # 2. Exportar BOM (Lista de Materiales)
            bom_file = os.path.join(export_dir, "BOM.csv")
            self._export_bom(board, bom_file)
            
            # 3. Exportar Posiciones XY
            xy_file = os.path.join(export_dir, "Posiciones_XY.csv")
            self._export_xy(board, xy_file)

            wx.MessageBox(
                f"✅ Archivos exportados correctamente en:\n{export_dir}\n\n"
                f"Contenido:\n"
                f"- Gerbers: {len(exported_gerbers)} capas\n"
                f"- BOM (Lista de materiales)\n"
                f"- Posiciones de componentes",
                "Exportación Exitosa",
                wx.OK | wx.ICON_INFORMATION
            )

        except Exception as e:
            wx.MessageBox(
                f"❌ Error en la exportación:\n{str(e)}",
                "Error",
                wx.OK | wx.ICON_ERROR
            )

    def _export_gerbers(self, board, output_dir):
        """Exporta todas las capas Gerber habilitadas"""
        plot_controller = pcbnew.PLOT_CONTROLLER(board)
        plot_options = plot_controller.GetPlotOptions()
        
        # Configuración básica
        plot_options.SetOutputDirectory(output_dir)
        plot_options.SetSketchPadLineWidth(pcbnew.FromMM(0.1))
        plot_options.SetUseGerberAttributes(True)
        plot_options.SetUseAuxOrigin(True)

        # Capas a exportar
        layers = [
            ("F_Cu", pcbnew.F_Cu, "Top Copper"),
            ("B_Cu", pcbnew.B_Cu, "Bottom Copper"),
            ("F_Mask", pcbnew.F_Mask, "Top Solder Mask"),
            ("B_Mask", pcbnew.B_Mask, "Bottom Solder Mask"),
            ("F_SilkS", pcbnew.F_SilkS, "Top Silkscreen"),
            ("B_SilkS", pcbnew.B_SilkS, "Bottom Silkscreen"),
            ("Edge_Cuts", pcbnew.Edge_Cuts, "Board Outline")
        ]

        exported_layers = []
        for layer_name, layer_id, layer_desc in layers:
            if board.IsLayerEnabled(layer_id):
                plot_controller.SetLayer(layer_id)
                plot_controller.OpenPlotfile(layer_name, pcbnew.PLOT_FORMAT_GERBER, layer_desc)
                if plot_controller.PlotLayer():
                    exported_layers.append(layer_name)

        # Archivos de taladros
        drill_writer = pcbnew.EXCELLON_WRITER(board)
        drill_writer.SetOptions(False, True, board.GetDesignSettings().GetAuxOrigin(), False)
        drill_writer.CreateDrillandMapFilesSet(output_dir, True, False)

        plot_controller.ClosePlot()
        return exported_layers

    def _export_bom(self, board, output_file):
        """Genera un archivo CSV con la lista de materiales"""
        components = {}
        
        for footprint in board.GetFootprints():
            part_info = {
                'Designator': footprint.GetReference(),
                'Value': footprint.GetValue(),
                'Package': footprint.GetFPID().GetLibItemName(),
                'Quantity': 1
            }
            
            # Agrupa componentes idénticos
            key = f"{part_info['Value']}_{part_info['Package']}"
            if key in components:
                components[key]['Quantity'] += 1
                components[key]['Designator'] += f", {part_info['Designator']}"
            else:
                components[key] = part_info

        # Escribe el archivo CSV
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['Designator', 'Value', 'Package', 'Quantity'])
            writer.writeheader()
            writer.writerows(components.values())

    def _export_xy(self, board, output_file):
        """Exporta las posiciones de los componentes en formato CSV"""
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Designator', 'Valor', 'Paquete', 'PosX(mm)', 'PosY(mm)', 'Rotación', 'Capa'])
            
            for footprint in board.GetFootprints():
                pos = footprint.GetPosition()
                writer.writerow([
                    footprint.GetReference(),
                    footprint.GetValue(),
                    footprint.GetFPID().GetLibItemName(),
                    round(pcbnew.ToMM(pos.x), 2),
                    round(pcbnew.ToMM(pos.y), 2),
                    round(footprint.GetOrientationDegrees(), 1),
                    'Top' if footprint.IsFlipped() else 'Bottom'
                ])

PluginDemo().register()
