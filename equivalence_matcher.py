#!/usr/bin/env python3
"""
接口等价性匹配器
使用路径相似度、方法名相似度等多维度匹配
"""

import re
from typing import Dict, List, Tuple
from difflib import SequenceMatcher
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class MatchScore:
    """匹配得分"""
    path_similarity: float = 0.0
    method_similarity: float = 0.0
    name_similarity: float = 0.0
    param_similarity: float = 0.0
    total_score: float = 0.0
    
    def calculate_total(self, weights: Dict[str, float] = None):
        """计算总分"""
        if weights is None:
            weights = {
                'path': 0.4,
                'method': 0.3,
                'name': 0.2,
                'param': 0.1
            }
        
        self.total_score = (
            self.path_similarity * weights['path'] +
            self.method_similarity * weights['method'] +
            self.name_similarity * weights['name'] +
            self.param_similarity * weights['param']
        )
        return self.total_score

class EquivalenceMatcher:
    """接口等价性匹配器"""
    
    def __init__(self, threshold: float = 0.7):
        self.threshold = threshold
        
        # 常见字段映射关系
        self.common_mappings = {
            'add': 'create',
            'modify': 'update',
            'edit': 'update',
            'remove': 'delete',
            'del': 'delete',
            'query': 'get',
            'search': 'get',
            'list': 'getAll',
            'detail': 'getById',
            'info': 'getById',
            'save': 'create',
            'insert': 'create',
        }
        
    def match_endpoints(self, old_endpoints: Dict, new_endpoints: Dict) -> List[Tuple]:
        """匹配新旧接口"""
        matched_pairs = []
        
        # 将接口按路径分组
        old_by_path = self._group_by_normalized_path(old_endpoints)
        new_by_path = self._group_by_normalized_path(new_endpoints)
        
        # 首先尝试路径完全匹配
        for norm_path, old_endpoint_list in old_by_path.items():
            if norm_path in new_by_path:
                # 路径相同，进一步匹配具体接口
                for old_ep in old_endpoint_list:
                    for new_ep in new_by_path[norm_path]:
                        score = self.calculate_similarity(old_ep, new_ep)
                        if score.total_score >= self.threshold:
                            matched_pairs.append((old_ep, new_ep))
        
        # 对于未匹配的旧接口，尝试模糊匹配
        unmatched_old = [
            ep for ep in old_endpoints.values() 
            if not any(ep == old for old, _ in matched_pairs)
        ]
        unmatched_new = [
            ep for ep in new_endpoints.values()
            if not any(ep == new for _, new in matched_pairs)
        ]
        
        # 尝试模糊匹配
        for old_ep in unmatched_old:
            best_match = None
            best_score = 0
            
            for new_ep in unmatched_new:
                score = self.calculate_similarity(old_ep, new_ep)
                if score.total_score > best_score and score.total_score >= self.threshold:
                    best_score = score.total_score
                    best_match = new_ep
            
            if best_match:
                matched_pairs.append((old_ep, best_match))
                unmatched_new.remove(best_match)
        
        return matched_pairs
    
    def calculate_similarity(self, endpoint1, endpoint2) -> MatchScore:
        """计算两个接口的相似度"""
        score = MatchScore()
        
        # 1. 路径相似度
        score.path_similarity = self._calculate_path_similarity(
            endpoint1.path, endpoint2.path
        )
        
        # 2. HTTP方法相似度
        score.method_similarity = 1.0 if endpoint1.method == endpoint2.method else 0.0
        
        # 3. 名称相似度（处理方法名）
        score.name_similarity = self._calculate_name_similarity(
            endpoint1.handler, endpoint2.handler
        )
        
        # 4. 参数相似度（如果有参数信息）
        if hasattr(endpoint1, 'parameters') and hasattr(endpoint2, 'parameters'):
            score.param_similarity = self._calculate_param_similarity(
                endpoint1.parameters, endpoint2.parameters
            )
        
        # 计算总分
        score.calculate_total()
        
        return score
    
    def _group_by_normalized_path(self, endpoints: Dict):
        """按规范化后的路径分组"""
        grouped = defaultdict(list)
        
        for endpoint in endpoints.values():
            norm_path = self._normalize_path_for_matching(endpoint.path)
            grouped[norm_path].append(endpoint)
        
        return dict(grouped)
    
    def _normalize_path_for_matching(self, path: str) -> str:
        """规范化路径以便匹配"""
        # 移除API版本前缀
        path = re.sub(r'/api/v\d+/', '/api/', path)
        
        # 将路径参数归一化
        path = re.sub(r'/\{[^}]+\}', '/{param}', path)
        path = re.sub(r'/:[^/]+', '/{param}', path)
        path = re.sub(r'/<[^>]+>', '/{param}', path)
        
        # 转换为小写并移除首尾斜杠
        path = path.lower().strip('/')
        
        return path
    
    def _calculate_path_similarity(self, path1: str, path2: str) -> float:
        """计算路径相似度"""
        norm1 = self._normalize_path_for_matching(path1)
        norm2 = self._normalize_path_for_matching(path2)
        
        # 如果规范化后路径相同，得1分
        if norm1 == norm2:
            return 1.0
        
        # 使用序列匹配器
        return SequenceMatcher(None, norm1, norm2).ratio()
    
    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """计算方法名相似度"""
        # 处理驼峰命名
        name1_words = self._split_camel_case(name1.lower())
        name2_words = self._split_camel_case(name2.lower())
        
        # 检查是否有常见映射关系
        for word1 in name1_words:
            if word1 in self.common_mappings:
                mapped = self.common_mappings[word1]
                if mapped in name2_words or mapped in name2.lower():
                    return 0.8  # 有映射关系但不是完全相同
        
        # 检查是否有相同单词
        common_words = set(name1_words) & set(name2_words)
        if common_words:
            return 0.6 + (len(common_words) / max(len(name1_words), len(name2_words))) * 0.4
        
        # 使用字符串相似度
        return SequenceMatcher(None, name1.lower(), name2.lower()).ratio()
    
    def _split_camel_case(self, text: str) -> List[str]:
        """分割驼峰命名的字符串"""
        words = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)', text)
        return [w.lower() for w in words]
    
    def _calculate_param_similarity(self, params1: List, params2: List) -> float:
        """计算参数相似度"""
        if not params1 and not params2:
            return 1.0
        
        if not params1 or not params2:
            return 0.0
        
        # 简单实现：检查是否有相同参数
        common_params = set(params1) & set(params2)
        return len(common_params) / max(len(params1), len(params2))