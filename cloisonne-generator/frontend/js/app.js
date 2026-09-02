// 掐丝珐琅图片转Creo曲线生成器 V2.0 前端逻辑
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

// 图层开关
const layerToggles = {
  original: document.getElementById('layer-original'),
  regions: document.getElementById('layer-regions'),
  boundaries: document.getElementById('layer-boundaries'),
  svg: document.getElementById('layer-svg'),
};
const layerImages = {
  original: document.getElementById('img-original'),
  regions: document.getElementById('img-regions'),
  boundaries: document.getElementById('img-boundaries'),
};
const svgContainer = document.getElementById('svg-container');

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
  formData.append('min_wire_spacing_mm', document.getElementById('min-spacing').value);
  formData.append('min_radius_mm', document.getElementById('min-radius').value);
  formData.append('output_width_mm', document.getElementById('output-width').value);
  formData.append('smoothness', document.getElementById('smoothness').value / 100);
  formData.append('gen_outline', document.getElementById('gen-outline').checked);
  const selectedMode = document.querySelector('input[name="generate-mode"]:checked');
  formData.append('generate_mode', selectedMode ? selectedMode.value : 'cloisonne');

  try {
    const response = await fetch(`${API_BASE}/api/analyze`, {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || '分析失败');
    }
    currentResult = await response.json();
    renderResult(currentResult);
    setStatus('分析完成', 'ready');
  } catch (err) {
    console.error(err);
    setStatus('分析失败: ' + err.message, 'error');
    previewInfo.textContent = '错误: ' + err.message;
  } finally {
    isProcessing = false;
    btnAnalyze.disabled = false;
  }
});

// 渲染结果
function renderResult(result) {
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

  // 掐丝模式：曲线检查面板
  resultSummary.style.display = 'block';
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

// 初始化
setStatus('请上传图片', 'ready');
