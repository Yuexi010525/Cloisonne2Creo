// 掐丝珐琅图片转Creo曲线生成器 V2.2 前端逻辑
const API_BASE = '';

let currentFile = null;
let currentResult = null;
let isProcessing = false;

// DOM元素
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const btnSelectFile = document.getElementById('btn-select-file');
const btnAnalyze = document.getElementById('btn-analyze');
const btnExportSvg = document.getElementById('btn-export-svg');
const btnDownloadSvg = document.getElementById('btn-download-svg');
const btnDownloadDxf = document.getElementById('btn-download-dxf');
const btnDownloadIbl = document.getElementById('btn-download-ibl');
const btnDownloadJson = document.getElementById('btn-download-json');
const statusText = document.getElementById('status-text');
const statusDot = document.getElementById('status-dot');
const fileInfo = document.getElementById('file-info');
const fileName = document.getElementById('file-name');
const fileDims = document.getElementById('file-dims');
const resultSummary = document.getElementById('result-summary');
const previewPlaceholder = document.getElementById('preview-placeholder');
const previewStack = document.getElementById('preview-stack');
const previewInfo = document.getElementById('preview-info');
const colorInteract = document.getElementById('color-interact');
const colorParams = document.getElementById('color-params');
const lineartParams = document.getElementById('lineart-params');
const colorResultGrid = document.getElementById('color-result-grid');
const lineartResultGrid = document.getElementById('lineart-result-grid');
const autoDetectResult = document.getElementById('auto-detect-result');

// 图层开关
const layerToggles = {
  original: document.getElementById('layer-original'),
  regions: document.getElementById('layer-regions'),
  boundaries: document.getElementById('layer-boundaries'),
  binary: document.getElementById('layer-binary'),
  skeleton: document.getElementById('layer-skeleton'),
  pruned: document.getElementById('layer-pruned'),
  svg: document.getElementById('layer-svg'),
};
const layerImages = {
  original: document.getElementById('img-original'),
  regions: document.getElementById('img-regions'),
  boundaries: document.getElementById('img-boundaries'),
  binary: document.getElementById('img-binary'),
  skeleton: document.getElementById('img-skeleton'),
  pruned: document.getElementById('img-pruned'),
};
const svgContainer = document.getElementById('svg-container');

// 生成模式切换
function getCurrentMode() {
  const selected = document.querySelector('input[name="generate-mode"]:checked');
  return selected ? selected.value : 'auto';
}

function updateModeUI() {
  const mode = getCurrentMode();
  const isColor = (mode === 'cloisonne');
  const isLineart = (mode === 'lineart');
  const isAuto = (mode === 'auto');

  // 参数面板
  colorParams.style.display = (isColor || isAuto) ? 'block' : 'none';
  lineartParams.style.display = (isLineart || isAuto) ? 'block' : 'none';

  // Debug 图层
  document.querySelectorAll('.layer-color').forEach(el => el.style.display = (isColor || isAuto) ? '' : 'none');
  document.querySelectorAll('.layer-lineart').forEach(el => el.style.display = (isLineart || isAuto) ? '' : 'none');

  // 自动检测结果
  autoDetectResult.style.display = 'none';
  autoDetectResult.textContent = '';
}

document.querySelectorAll('input[name="generate-mode"]').forEach(radio => {
  radio.addEventListener('change', updateModeUI);
});

// 参数预设
const PRESETS = {
  'standard': { // 普通花纹
    color_precision: 6, filter_speckle: 4, hierarchical: 'cutout', mode: 'spline',
    min_region_area_mm2: 2.0, min_boundary_length_mm: 1.5,
    simplify_tolerance_mm: 0.15, wire_diameter_mm: 0.6,
    min_wire_spacing_mm: 0.8, min_radius_mm: 1.0, smoothness: 70,
  },
  'high-precision': { // 高精度细节
    color_precision: 12, filter_speckle: 2, hierarchical: 'cutout', mode: 'spline',
    min_region_area_mm2: 0.5, min_boundary_length_mm: 1.0,
    simplify_tolerance_mm: 0.08, wire_diameter_mm: 0.6,
    min_wire_spacing_mm: 0.6, min_radius_mm: 0.8, smoothness: 50,
  },
  'fast-preview': { // 快速预览
    color_precision: 4, filter_speckle: 8, hierarchical: 'cutout', mode: 'spline',
    min_region_area_mm2: 4.0, min_boundary_length_mm: 2.5,
    simplify_tolerance_mm: 0.25, wire_diameter_mm: 0.6,
    min_wire_spacing_mm: 1.0, min_radius_mm: 1.5, smoothness: 80,
  },
};

// 文件选择
btnSelectFile.addEventListener('click', () => fileInput.click());
dropZone.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', (e) => {
  if (e.target.files.length > 0) handleFile(e.target.files[0]);
});

// 拖拽
dropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropZone.classList.add('dragover');
});
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('dragover');
  if (e.dataTransfer.files.length > 0) handleFile(e.dataTransfer.files[0]);
});

// 参数预设下拉框
document.getElementById('preset-select').addEventListener('change', (e) => {
  const preset = PRESETS[e.target.value];
  if (!preset) return;
  document.getElementById('color-precision').value = preset.color_precision;
  document.getElementById('filter-speckle').value = preset.filter_speckle;
  document.getElementById('hierarchical').value = preset.hierarchical;
  document.getElementById('curve-mode').value = preset.mode;
  document.getElementById('min-region').value = preset.min_region_area_mm2;
  document.getElementById('min-boundary').value = preset.min_boundary_length_mm;
  document.getElementById('simplify-tol').value = preset.simplify_tolerance_mm;
  document.getElementById('wire-diameter').value = preset.wire_diameter_mm;
  document.getElementById('min-spacing').value = preset.min_wire_spacing_mm;
  document.getElementById('min-radius').value = preset.min_radius_mm;
  document.getElementById('smoothness').value = preset.smoothness;
  document.getElementById('smoothness-val').textContent = preset.smoothness + '%';
  setStatus(`已应用预设: ${e.target.selectedOptions[0].text}`, 'ready');
});

// 平滑slider联动
document.getElementById('smoothness').addEventListener('input', (e) => {
  document.getElementById('smoothness-val').textContent = e.target.value + '%';
});

function handleFile(file) {
  if (!file.type.startsWith('image/')) {
    setStatus('请选择图片文件', 'error');
    return;
  }
  currentFile = file;
  fileName.textContent = file.name;
  const img = new Image();
  img.onload = () => {
    fileDims.textContent = `${img.naturalWidth} × ${img.naturalHeight} px`;
  };
  img.src = URL.createObjectURL(file);
  fileInfo.style.display = 'block';
  btnAnalyze.disabled = false;
  setStatus('图片已加载，点击"开始分析"', 'ready');
}

// 分析按钮
btnAnalyze.addEventListener('click', async () => {
  if (!currentFile || isProcessing) return;
  isProcessing = true;
  btnAnalyze.disabled = true;
  btnExportSvg.disabled = true;
  btnDownloadSvg.disabled = true;
  btnDownloadDxf.disabled = true;
  btnDownloadIbl.disabled = true;
  btnDownloadJson.disabled = true;
  setStatus('正在分析...', 'processing');

  const formData = new FormData();
  formData.append('file', currentFile);
  formData.append('color_precision', document.getElementById('color-precision').value);
  formData.append('filter_speckle', document.getElementById('filter-speckle').value);
  formData.append('hierarchical', document.getElementById('hierarchical').value);
  formData.append('mode', document.getElementById('curve-mode').value);
  formData.append('min_region_area_mm2', document.getElementById('min-region').value);
  formData.append('min_boundary_length_mm', document.getElementById('min-boundary').value);
  formData.append('simplify_tolerance_mm', document.getElementById('simplify-tol').value);
  formData.append('wire_diameter_mm', document.getElementById('wire-diameter').value);
  formData.append('recommended_spacing_mm', document.getElementById('min-spacing').value);
  formData.append('min_radius_mm', document.getElementById('min-radius').value);
  formData.append('output_width_mm', document.getElementById('output-width').value);
  formData.append('smoothness', document.getElementById('smoothness').value / 100);
  formData.append('gen_outline', document.getElementById('gen-outline').checked);
  // 线稿参数
  const bt = document.getElementById('la-binary-threshold').value;
  formData.append('binary_threshold', bt === 'auto' ? '' : bt);
  formData.append('denoise_ksize', document.getElementById('la-denoise').value);
  formData.append('min_spur_length_mm', document.getElementById('la-spur').value);
  formData.append('keep_fine_segments', document.getElementById('la-keep-fine').checked);
  formData.append('skeleton_method', document.getElementById('la-skeleton').value);
  formData.append('graph_engine', document.getElementById('la-graph-engine').value);
  const selectedMode = document.querySelector('input[name="generate-mode"]:checked');
  formData.append('gen_mode', selectedMode ? selectedMode.value : 'auto');

  let data;

  try {
    const response = await fetch(`${API_BASE}/api/analyze`, {
      method: 'POST',
      body: formData,
      cache: 'no-store',
    });
    if (!response.ok) {
      let message = `HTTP ${response.status}`;
      try {
        const err = await response.json();
        message = err.detail || message;
      } catch (_) {}
      throw new Error(`后端分析失败: ${message}`);
    }
    data = await response.json();
  } catch (err) {
    console.error('[API ERROR]', err);
    setStatus('后端分析失败: ' + err.message, 'error');
    previewInfo.textContent = '后端错误: ' + err.message;
    isProcessing = false;
    btnAnalyze.disabled = false;
    return;
  }

  try {
    currentResult = data;
    renderResult(currentResult);
    setStatus('分析完成', 'ready');
  } catch (err) {
    console.error('[RENDER ERROR]', err);
    console.error('[RESULT DATA]', data);
    setStatus('分析成功，但界面渲染失败', 'error');
    previewInfo.textContent = '结果已返回，但前端显示失败: ' + err.message;
  } finally {
    isProcessing = false;
    btnAnalyze.disabled = false;
  }
});

// 渲染结果
function renderResult(result) {
  console.group('[renderResult]');
  console.log('mode =', result?.mode);
  console.log('engine =', result?.engine);
  console.log('keys =', result ? Object.keys(result) : null);
  console.log('validation =', result?.validation);
  console.log('strokes =', result?.strokes);
  console.log('preview_images =', result?.preview_images);
  console.groupEnd();
  // 检查是否为非掐丝模式（svg/outline直接返回原始SVG）
  if (result.mode === 'svg' || result.mode === 'outline') {
    resultSummary.style.display = 'none';
    colorInteract.style.display = 'none';
    previewPlaceholder.style.display = 'none';
    previewStack.style.display = 'block';
    if (currentFile) {
      layerImages.original.src = URL.createObjectURL(currentFile);
      layerImages.original.style.display = 'block';
    }
    layerImages.regions.style.display = 'none';
    layerImages.boundaries.style.display = 'none';
    svgContainer.style.display = 'block';
    svgContainer.innerHTML = result.svg;
    const svg = svgContainer.querySelector('svg');
    if (svg) {
      svg.style.position = 'absolute';
      svg.style.top = '0';
      svg.style.left = '0';
      svg.style.width = '100%';
      svg.style.height = '100%';
    }
    previewInfo.textContent = `模式: ${result.mode === 'svg' ? '普通SVG' : '仅轮廓'} | 尺寸: ${result.image_info.width_px}×${result.image_info.height_px}px`;
    btnExportSvg.disabled = false;
    btnDownloadSvg.disabled = false;
    btnDownloadDxf.disabled = true;
    btnDownloadIbl.disabled = true;
    btnDownloadJson.disabled = true;
    return;
  }

  // 线稿模式 (V2.2)
  if (result.mode === 'lineart' || result.engine === 'lineart_skeleton') {
    resultSummary.style.display = 'block';
    colorResultGrid.style.display = 'none';
    lineartResultGrid.style.display = 'grid';
    colorInteract.style.display = 'none';

    // 防御式默认值
    const ls = result.lineart_stats || {};
    const v = result.validation || {};
    const strokes = Array.isArray(result.strokes) ? result.strokes : [];
    const branches = Array.isArray(result.branches) ? result.branches : [];
    const junctions = Array.isArray(result.junctions) ? result.junctions : [];
    const endpoints = Array.isArray(result.endpoints) ? result.endpoints : [];
    const mergedCurves = Array.isArray(result.merged_curves) ? result.merged_curves : [];
    const previewImages = result.preview_images || {};
    const imageInfo = result.image_info || {};

    // 统计多级 fallback: ls -> v -> 数组长度
    const strokeCount = ls.raw_branch_count ?? v.raw_branch_count ?? strokes.length;
    const branchCount = ls.branch_count ?? v.branch_count ?? branches.length;
    const junctionCount = ls.junction_count ?? v.junction_count ?? junctions.length;
    const endpointCount = ls.endpoint_count ?? v.endpoint_count ?? endpoints.length;
    const finalCurveCount = ls.final_curve_count ?? v.final_curve_count ?? Object.keys(result.centerlines || {}).length;
    const mergedCount = ls.merged_curve_count ?? v.merged_curve_count ?? mergedCurves.length;

    document.getElementById('res-la-strokes').textContent = strokeCount;
    document.getElementById('res-la-branches').textContent = branchCount;
    document.getElementById('res-la-junctions').textContent = junctionCount;
    document.getElementById('res-la-endpoints').textContent = endpointCount;
    document.getElementById('res-la-curves').textContent = finalCurveCount;
    document.getElementById('res-la-merged').textContent = mergedCount;
    document.getElementById('res-la-hard').textContent = v.hard_collision_count ?? 0;
    document.getElementById('res-la-dense').textContent = v.dense_spacing_warning_count ?? 0;
    document.getElementById('res-la-intersect').textContent = v.self_intersection_count ?? v.intersection_count ?? 0;
    document.getElementById('res-la-smallradius').textContent = v.small_radius_count ?? 0;

    const valStatus = document.getElementById('res-validation');
    const statusText = v.status === 'ok' ? '通过 ✓' : v.status === 'error' ? '错误 ✗' : '警告 ⚠';
    let valText = `验证状态: ${statusText}`;
    if ((v.hard_collision_count ?? 0) > 0) valText += ` | 实体碰撞: ${v.hard_collision_count}`;
    if ((v.dense_spacing_warning_count ?? 0) > 0) valText += ` | 过密区域: ${v.dense_spacing_warning_count}`;
    valStatus.textContent = valText;
    valStatus.className = `val-status ${v.status || 'ok'}`;

    // 自动检测结果
    if (result.auto_detection) {
      autoDetectResult.style.display = 'block';
      const ad = result.auto_detection;
      autoDetectResult.textContent = `自动检测: ${ad.mode === 'lineart' ? '黑白线稿' : '彩色图'}`;
    } else {
      autoDetectResult.style.display = 'none';
    }

    // 预览图
    previewPlaceholder.style.display = 'none';
    previewStack.style.display = 'block';
    if (currentFile) {
      layerImages.original.src = URL.createObjectURL(currentFile);
      layerImages.original.style.display = layerToggles.original.checked ? 'block' : 'none';
    }

    // 线稿调试图层 (防御式循环)
    const debugImageMap = {
      binary: 'binary',
      skeleton: 'skeleton',
      pruned: 'pruned_skeleton',
    };
    for (const [key, serverKey] of Object.entries(debugImageMap)) {
      const target = layerImages[key];
      if (!target) {
        console.warn(`[LineArt] 缺少DOM元素: ${key}`);
        continue;
      }
      if (previewImages[serverKey]) {
        target.src = `data:image/png;base64,${previewImages[serverKey]}`;
        target.style.display = layerToggles[key]?.checked ? 'block' : 'none';
      } else {
        target.style.display = 'none';
      }
    }

    // 隐藏彩色图层
    layerImages.regions.style.display = 'none';
    layerImages.boundaries.style.display = 'none';

    loadSvg();

    const widthMm = imageInfo.output_width_mm ?? '-';
    const heightMm = imageInfo.output_height_mm ?? '-';
    previewInfo.textContent =
      `引擎: ${result.engine ?? '-'} (${v.graph_engine ?? 'skan'}) | ` +
      `Stroke: ${strokeCount} | Curve: ${finalCurveCount} | ` +
      `合并: ${mergedCount} | 碰撞: ${v.hard_collision_count ?? 0} | ` +
      `过密: ${v.dense_spacing_warning_count ?? 0} | 输出: ${widthMm}×${heightMm}mm`;

    btnExportSvg.disabled = false;
    btnDownloadSvg.disabled = false;
    btnDownloadDxf.disabled = !result.dxf_base64;
    btnDownloadIbl.disabled = !result.ibl_text;
    btnDownloadJson.disabled = false;
    return;
  }

  // 掐丝模式：曲线检查面板
  resultSummary.style.display = 'block';
  colorResultGrid.style.display = 'grid';
  lineartResultGrid.style.display = 'none';
  document.getElementById('res-regions').textContent = result.regions.length;
  document.getElementById('res-boundaries').textContent = result.boundaries.length;
  document.getElementById('res-merged').textContent =
    result.merged_curves ? result.merged_curves.length : '-';

  const v = result.validation;
  document.getElementById('res-short').textContent = v.short_boundary_count || 0;
  document.getElementById('res-broken').textContent = v.broken_curve_count || 0;
  document.getElementById('res-intersect').textContent = v.intersection_count || 0;
  document.getElementById('res-spacing').textContent = v.spacing_violation_count || 0;
  document.getElementById('res-smallradius').textContent = v.small_radius_count || 0;

  const valStatus = document.getElementById('res-validation');
  valStatus.textContent = `验证状态: ${v.status === 'ok' ? '通过 ✓' :
    v.status === 'error' ? '错误 ✗' : '警告 ⚠'}`;
  valStatus.className = `val-status ${v.status}`;

  // 颜色交互面板
  renderColorInteraction(result);

  // 显示预览图
  previewPlaceholder.style.display = 'none';
  previewStack.style.display = 'block';

  if (currentFile) {
    layerImages.original.src = URL.createObjectURL(currentFile);
    layerImages.original.style.display = layerToggles.original.checked ? 'block' : 'none';
  }
  if (result.preview_images) {
    if (result.preview_images.regions) {
      layerImages.regions.src = `data:image/png;base64,${result.preview_images.regions}`;
      layerImages.regions.style.display = layerToggles.regions.checked ? 'block' : 'none';
    } else {
      layerImages.regions.style.display = 'none';
    }
    if (result.preview_images.boundaries) {
      layerImages.boundaries.src = `data:image/png;base64,${result.preview_images.boundaries}`;
      layerImages.boundaries.style.display = layerToggles.boundaries.checked ? 'block' : 'none';
    } else {
      layerImages.boundaries.style.display = 'none';
    }
  }

  loadSvg();

  previewInfo.textContent =
    `引擎: ${result.engine} | 区域: ${result.regions.length} | 边界: ${result.boundaries.length} | ` +
    `连续组: ${result.merged_curves ? result.merged_curves.length : '-'} | ` +
    `自交: ${v.intersection_count} | 线距冲突: ${v.spacing_violation_count} | ` +
    `输出: ${result.image_info.output_width_mm}×${result.image_info.output_height_mm}mm`;

  btnExportSvg.disabled = false;
  btnDownloadSvg.disabled = false;
  btnDownloadDxf.disabled = !result.has_dxf;
  btnDownloadIbl.disabled = !result.has_ibl;
  btnDownloadJson.disabled = false;
}

// 颜色交互（规格书四十五章：点击颜色高亮Region及其相邻Region，显示共享边界数量）
function renderColorInteraction(result) {
  colorInteract.style.display = 'block';
  const listEl = document.getElementById('color-list');
  const neighborsEl = document.getElementById('color-neighbors');
  listEl.innerHTML = '';
  neighborsEl.innerHTML = '';

  // 用regions数据构建颜色chip（区域颜色）
  const palette = result.color_palette || [];
  const regions = result.regions || [];
  const boundaries = result.boundaries || [];

  // 每个区域的颜色和邻居
  const regionByColor = {};
  regions.forEach(r => {
    if (!regionByColor[r.color_id]) regionByColor[r.color_id] = [];
    regionByColor[r.color_id].push(r);
  });

  palette.forEach((color, idx) => {
    const chip = document.createElement('div');
    chip.className = 'color-chip';
    chip.style.background = color.hex;
    chip.title = `颜色${idx}: ${color.hex}`;
    const label = document.createElement('span');
    label.className = 'chip-label';
    label.textContent = `R${idx}`;
    chip.appendChild(label);
    chip.dataset.colorId = idx;

    chip.addEventListener('click', () => {
      // 选中态
      document.querySelectorAll('.color-chip').forEach(c => c.classList.remove('selected'));
      chip.classList.add('selected');
      // 显示邻居和共享边界
      const regionIds = (regionByColor[idx] || []).map(r => r.id);
      if (regionIds.length === 0) {
        neighborsEl.innerHTML = `<div>颜色 R${idx} 无对应区域</div>`;
        return;
      }
      // 找所有与该颜色区域相邻的边界
      const connected = new Map(); // regionId -> boundary count
      let boundaryTotal = 0;
      boundaries.forEach(b => {
        const touches = regionIds.includes(b.region_a) || regionIds.includes(b.region_b);
        if (touches) {
          boundaryTotal++;
          const other = regionIds.includes(b.region_a) ? b.region_b : b.region_a;
          if (other >= 0) connected.set(other, (connected.get(other) || 0) + 1);
        }
      });
      let html = `<div class="neighbor-row"><strong>颜色 R${idx}</strong> (${color.hex})</div>`;
      html += `<div class="neighbor-row">共享边界总数: <strong>${boundaryTotal}</strong></div>`;
      html += `<div class="neighbor-row">相邻区域 (${connected.size}):</div>`;
      connected.forEach((count, otherId) => {
        const otherColor = palette[otherId];
        html += `<div class="neighbor-row">
          <span class="mini-chip" style="background:${otherColor ? otherColor.hex : '#888'}"></span>
          <span>R${otherId} — 共享 ${count} 条边界</span>
        </div>`;
      });
      neighborsEl.innerHTML = html;
    });
    listEl.appendChild(chip);
  });

  neighborsEl.innerHTML = '<div>点击上方颜色查看相邻区域与共享边界</div>';
}

// 加载SVG预览
async function loadSvg() {
  try {
    const resp = await fetch(`${API_BASE}/api/svg`);
    if (resp.ok) {
      const svgText = await resp.text();
      svgContainer.innerHTML = svgText;
      const svg = svgContainer.querySelector('svg');
      if (svg) {
        svg.style.position = 'absolute';
        svg.style.top = '0';
        svg.style.left = '0';
        svg.style.width = '100%';
        svg.style.height = '100%';
      }
      svgContainer.style.display = layerToggles.svg.checked ? 'block' : 'none';
    }
  } catch (e) {
    console.warn('SVG加载失败', e);
  }
}

// 导出/下载SVG
btnExportSvg.addEventListener('click', () => {
  window.open(`${API_BASE}/api/svg`, '_blank');
});
btnDownloadSvg.addEventListener('click', () => {
  const a = document.createElement('a');
  a.href = `${API_BASE}/api/download/svg`;
  a.download = 'cloisonne_curves.svg';
  a.click();
});

// 下载DXF / IBL / JSON
btnDownloadDxf.addEventListener('click', () => {
  const a = document.createElement('a');
  a.href = `${API_BASE}/api/download/dxf`;
  a.download = 'cloisonne_curves.dxf';
  a.click();
});
btnDownloadIbl.addEventListener('click', () => {
  const a = document.createElement('a');
  a.href = `${API_BASE}/api/download/ibl`;
  a.download = 'cloisonne_curves.ibl';
  a.click();
});
btnDownloadJson.addEventListener('click', () => {
  const a = document.createElement('a');
  a.href = `${API_BASE}/api/download/json`;
  a.download = 'cloisonne_project.json';
  a.click();
});

// 图层开关
Object.keys(layerToggles).forEach(key => {
  layerToggles[key].addEventListener('change', (e) => {
    if (key === 'svg') {
      svgContainer.style.display = e.target.checked ? 'block' : 'none';
    } else {
      layerImages[key].style.display = e.target.checked ? 'block' : 'none';
    }
  });
});

// 状态设置
function setStatus(text, type) {
  statusText.textContent = text;
  statusDot.className = `status-dot ${type}`;
}

// DOM ID 启动检查
function checkRequiredDom() {
  const required = [
    'btn-analyze', 'result-summary', 'color-result-grid', 'lineart-result-grid',
    'res-la-strokes', 'res-la-branches', 'res-la-junctions', 'res-la-endpoints',
    'res-la-curves', 'res-la-merged', 'res-la-hard', 'res-la-dense',
    'res-la-intersect', 'res-la-smallradius', 'res-validation',
    'preview-info', 'svg-container', 'img-original',
    'img-binary', 'img-skeleton', 'img-pruned',
  ];
  const missing = required.filter(id => !document.getElementById(id));
  if (missing.length > 0) {
    console.error('[DOM CHECK] Missing:', missing);
    return false;
  }
  console.log('[DOM CHECK] OK');
  return true;
}

// 初始化
setStatus('请上传图片', 'ready');
checkRequiredDom();
updateModeUI();
