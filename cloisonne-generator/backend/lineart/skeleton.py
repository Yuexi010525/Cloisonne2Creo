# -*- coding: utf-8 -*-
"""
LineArtSkeleton - 骨架化
规格书(V2.1线稿模式): 调用 scikit-image skeletonize, 不自研骨架算法。
默认 Skeletonize, medial_axis 作为未来选项。
"""
import numpy as np


class LineArtSkeleton:
    def __init__(self, config=None):
        self.config = config or {}
        # 算法: "skeletonize" (默认) / "thin" / "medial_axis"
        self.method = self.config.get("skeleton_method", "skeletonize")

    def skeletonize(self, mask):
        """
        输入: 二值Mask (True=前景)
        输出: 骨架Mask (True=骨架像素)
        """
        if self.method == "thin":
            from skimage.morphology import thin
            skel = thin(mask)
        elif self.method == "medial_axis":
            from skimage.morphology import medial_axis
            skel = medial_axis(mask)
            if isinstance(skel, tuple):
                skel = skel[0]
        else:
            from skimage.morphology import skeletonize
            skel = skeletonize(mask)
        return skel.astype(bool)
