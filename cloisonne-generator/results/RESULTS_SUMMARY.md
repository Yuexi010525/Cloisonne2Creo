# 掐丝珐琅图片转 Creo 曲线生成器 - 多轮生成结果汇总

生成时间: 自动

| 轮次 | 图片 | 耗时(s) | 区域 | 边界 | 连续组 | 外轮廓 | 状态 | 短边界 | 断线 | 自交 | 线距冲突 | 小半径 |
|------|------|--------|------|------|--------|--------|------|--------|------|------|----------|--------|
| R01_test01_基础两色块 | test01_two_colors.png | 0.48 | 2 | 1 | 1 | 0 | ok | 0 | 0 | 0 | 0 | 0 |
| R02_test03_花朵_普通 | test03_flower.png | 1.4 | 14 | 20 | 19 | 0 | warning | 0 | 0 | 0 | 16 | 0 |
| R03_test03_花朵_高精度 | test03_flower.png | 1.37 | 14 | 20 | 20 | 0 | warning | 0 | 0 | 0 | 10 | 0 |
| R04_test03_花朵_快速预览 | test03_flower.png | 1.34 | 14 | 20 | 20 | 0 | warning | 1 | 0 | 0 | 21 | 0 |
| R05_test04_卡通猫_外轮廓 | test04_cat.png | 3.14 | 15 | 21 | 21 | 0 | warning | 0 | 0 | 0 | 7 | 4 |
| R06_test02_三色块_SVG模式 | test02_three_colors.png | 0.11 | 4 | 5 | 4 | 0 | warning | 0 | 0 | 0 | 1 | 0 |

## 各轮详细参数

### R01_test01_基础两色块
- 图片: `test01_two_colors.png`
- 参数: `{"color_precision": 6, "filter_speckle": 4, "hierarchical": "cutout", "mode": "spline", "min_region_area_mm2": 1.0, "min_boundary_length_mm": 1.5, "simplify_tolerance_mm": 0.15, "wire_diameter_mm": 0.6, "min_wire_spacing_mm": 0.8, "min_radius_mm": 1.0, "output_width_mm": 100, "generate_mode": "cloisonne", "smoothness": 0.7, "gen_outline": false}`
- 输出文件: result.json / preview.svg (DXF/IBL在JSON内嵌)

### R02_test03_花朵_普通
- 图片: `test03_flower.png`
- 参数: `{"color_precision": 6, "filter_speckle": 4, "hierarchical": "cutout", "mode": "spline", "min_region_area_mm2": 1.0, "min_boundary_length_mm": 1.5, "simplify_tolerance_mm": 0.15, "wire_diameter_mm": 0.6, "min_wire_spacing_mm": 0.8, "min_radius_mm": 1.0, "output_width_mm": 100, "generate_mode": "cloisonne", "smoothness": 0.7, "gen_outline": false}`
- 输出文件: result.json / preview.svg (DXF/IBL在JSON内嵌)

### R03_test03_花朵_高精度
- 图片: `test03_flower.png`
- 参数: `{"color_precision": 12, "filter_speckle": 2, "hierarchical": "cutout", "mode": "spline", "min_region_area_mm2": 0.5, "min_boundary_length_mm": 1.0, "simplify_tolerance_mm": 0.08, "wire_diameter_mm": 0.6, "min_wire_spacing_mm": 0.6, "min_radius_mm": 0.8, "output_width_mm": 120, "generate_mode": "cloisonne", "smoothness": 0.5, "gen_outline": true}`
- 输出文件: result.json / preview.svg (DXF/IBL在JSON内嵌)

### R04_test03_花朵_快速预览
- 图片: `test03_flower.png`
- 参数: `{"color_precision": 4, "filter_speckle": 8, "hierarchical": "cutout", "mode": "spline", "min_region_area_mm2": 4.0, "min_boundary_length_mm": 2.0, "simplify_tolerance_mm": 0.25, "wire_diameter_mm": 0.6, "min_wire_spacing_mm": 1.0, "min_radius_mm": 1.2, "output_width_mm": 100, "generate_mode": "cloisonne", "smoothness": 0.3, "gen_outline": false}`
- 输出文件: result.json / preview.svg (DXF/IBL在JSON内嵌)

### R05_test04_卡通猫_外轮廓
- 图片: `test04_cat.png`
- 参数: `{"color_precision": 6, "filter_speckle": 4, "hierarchical": "cutout", "mode": "spline", "min_region_area_mm2": 1.0, "min_boundary_length_mm": 1.5, "simplify_tolerance_mm": 0.15, "wire_diameter_mm": 0.6, "min_wire_spacing_mm": 0.8, "min_radius_mm": 1.0, "output_width_mm": 100, "generate_mode": "cloisonne", "smoothness": 0.7, "gen_outline": true}`
- 输出文件: result.json / preview.svg (DXF/IBL在JSON内嵌)

### R06_test02_三色块_SVG模式
- 图片: `test02_three_colors.png`
- 参数: `{"color_precision": 6, "filter_speckle": 4, "hierarchical": "cutout", "mode": "spline", "min_region_area_mm2": 1.0, "min_boundary_length_mm": 1.0, "simplify_tolerance_mm": 0.15, "wire_diameter_mm": 0.6, "min_wire_spacing_mm": 0.8, "min_radius_mm": 1.0, "output_width_mm": 100, "generate_mode": "svg", "smoothness": 0.7, "gen_outline": false}`
- 输出文件: result.json / preview.svg (DXF/IBL在JSON内嵌)

