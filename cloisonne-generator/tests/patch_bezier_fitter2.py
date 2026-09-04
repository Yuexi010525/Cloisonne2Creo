# -*- coding: utf-8 -*-
"""Harden BezierFitter against recursive explosion:
1) enforce max_segments in _fit_curve (previously unused -> recursive blowup)
2) lower fit point cap 1500 -> 1000, distance samples 20 -> 12
"""
p = r'F:\000-deepseek\掐丝模型生成器\cloisonne-generator\backend\curve\bezier_fitter.py'
d = open(p, 'rb').read().decode('utf-8')

# 1) point cap 1500 -> 1000
d = d.replace('MAX_FIT_POINTS = 1500', 'MAX_FIT_POINTS = 1000')

# 2) _fit_curve signature + segment cap
old_sig = '''    def _fit_curve(self, points, start, end, depth=0):
        """递归拟合：如果误差超过阈值，则在最大误差点拆分"""
        if depth > 20 or (end - start) < 2:
            return [self._fit_single_segment(points[start:end+1])]'''
new_sig = '''    def _fit_curve(self, points, start, end, depth=0, seg_count=0):
        """递归拟合：如果误差超过阈值，则在最大误差点拆分
        V2.3.2: max_segments 硬上限 + 深度上限, 防止复杂边界递归爆炸"""
        if depth > 12 or (end - start) < 2 or seg_count >= self.max_segments:
            return [self._fit_single_segment(points[start:end+1])]'''
assert old_sig in d, 'fit_curve sig not found'
d = d.replace(old_sig, new_sig)

# 3) recursive calls pass seg_count
old_rec = '''            left = self._fit_curve(points, start, max_idx, depth + 1)
            right = self._fit_curve(points, max_idx, end, depth + 1)
            return left + right'''
new_rec = '''            left = self._fit_curve(points, start, max_idx, depth + 1, seg_count)
            right = self._fit_curve(points, max_idx, end, depth + 1, seg_count + len(left))
            return left + right'''
assert old_rec in d, 'recursion not found'
d = d.replace(old_rec, new_rec)

# 4) samples 20 -> 12
old_samp = '    def _point_to_bezier_distance(self, point, bezier, samples=20):'
new_samp = '    def _point_to_bezier_distance(self, point, bezier, samples=12):'
assert old_samp in d, 'samples not found'
d = d.replace(old_samp, new_samp)

open(p, 'wb').write(d.encode('utf-8'))
print('patched bezier_fitter (max_segments cap + tighter decimate/samples)')
