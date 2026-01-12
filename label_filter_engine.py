"""
Label Filtering Engine - Replicates Excel filtering system with wildcards

Supports:
- Multiple cascading blocker stages (Bs1, Bs2, Bs3, Bs4)
- Target filtering stage (Ts)
- Wildcard patterns (* and ?)
- Negative filters (invert matching)
- Cumulative filtering (each stage filters the output of the previous stage)
"""

import re
from typing import List, Dict, Any
import json


class LabelFilter:
    """Individual filter with pattern and action"""

    def __init__(self, pattern: str, action: str = 'block', enabled: bool = True):
        """
        Args:
            pattern: Search pattern (supports * and ? wildcards)
            action: 'block' to exclude matches, 'include' to include only matches
            enabled: Whether this filter is active
        """
        self.pattern = pattern
        self.action = action
        self.enabled = enabled
        self._regex = self._convert_wildcard_to_regex(pattern)

    def _convert_wildcard_to_regex(self, pattern: str) -> re.Pattern:
        """Convert Excel-style wildcards to regex"""
        # Escape special regex characters except * and ?
        escaped = re.escape(pattern)
        # Convert wildcards: * -> .* (any chars), ? -> . (single char)
        regex_pattern = escaped.replace(r'\*', '.*').replace(r'\?', '.')
        # Case-insensitive by default (like Excel SEARCH function)
        return re.compile(regex_pattern, re.IGNORECASE)

    def matches(self, label: str) -> bool:
        """Check if label matches this filter pattern"""
        if not self.enabled:
            return False
        return self._regex.search(label) is not None

    def should_keep(self, label: str) -> bool:
        """
        Determine if label should be kept based on filter action

        Returns:
            True if label should be kept, False if it should be filtered out
        """
        if not self.enabled:
            return True  # Disabled filters don't affect anything

        matches = self.matches(label)

        if self.action == 'block':
            # Block action: remove if it matches
            return not matches
        elif self.action == 'include':
            # Include action: keep only if it matches
            return matches
        else:
            return True


class FilterStage:
    """A stage of filtering (e.g., Bs1, Bs2, Ts)"""

    def __init__(self, name: str, filters: List[LabelFilter] = None):
        """
        Args:
            name: Stage name (e.g., 'Bs1', 'Ts')
            filters: List of filters to apply in this stage
        """
        self.name = name
        self.filters = filters or []

    def apply(self, labels: List[str]) -> List[str]:
        """
        Apply all filters in this stage to the label list

        Returns:
            Filtered list of labels
        """
        result = labels.copy()

        for filter in self.filters:
            if not filter.enabled:
                continue

            # Apply filter to current result
            result = [label for label in result if filter.should_keep(label)]

        return result

    def add_filter(self, pattern: str, action: str = 'block', enabled: bool = True):
        """Add a new filter to this stage"""
        self.filters.append(LabelFilter(pattern, action, enabled))

    def to_dict(self) -> Dict[str, Any]:
        """Export stage configuration as dictionary"""
        return {
            'name': self.name,
            'filters': [
                {
                    'pattern': f.pattern,
                    'action': f.action,
                    'enabled': f.enabled
                }
                for f in self.filters
            ]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FilterStage':
        """Create FilterStage from dictionary"""
        stage = cls(data['name'])
        for f in data['filters']:
            stage.add_filter(f['pattern'], f['action'], f['enabled'])
        return stage


class LabelFilterEngine:
    """
    Complete label filtering engine with multiple cascading stages
    """

    def __init__(self):
        """Initialize empty filter engine"""
        self.blocker_stages: List[FilterStage] = []
        self.target_stage: FilterStage = None
        self.source_labels: List[str] = []

    def set_source_labels(self, labels: List[str]):
        """Set the source label list"""
        self.source_labels = labels.copy()

    def add_blocker_stage(self, name: str) -> FilterStage:
        """Add a new blocker stage"""
        stage = FilterStage(name)
        self.blocker_stages.append(stage)
        return stage

    def set_target_stage(self, name: str) -> FilterStage:
        """Set/create the target stage"""
        self.target_stage = FilterStage(name)
        return self.target_stage

    def apply_filters(self, labels: List[str] = None) -> List[str]:
        """
        Apply all filter stages to get final filtered list

        Args:
            labels: Starting label list (uses source_labels if not provided)

        Returns:
            Final filtered label list
        """
        if labels is None:
            labels = self.source_labels

        result = labels.copy()

        # Apply blocker stages in sequence
        for stage in self.blocker_stages:
            result = stage.apply(result)

        # Apply target stage if it exists
        if self.target_stage:
            result = self.target_stage.apply(result)

        return result

    def get_stage_results(self, labels: List[str] = None) -> Dict[str, List[str]]:
        """
        Get results after each stage for visualization

        Returns:
            Dictionary mapping stage name to filtered results
        """
        if labels is None:
            labels = self.source_labels

        results = {
            'source': labels.copy()
        }

        current = labels.copy()

        # Apply each blocker stage and record results
        for stage in self.blocker_stages:
            current = stage.apply(current)
            results[stage.name] = current.copy()

        # Apply target stage
        if self.target_stage:
            current = self.target_stage.apply(current)
            results[self.target_stage.name] = current.copy()

        results['final'] = current

        return results

    def save_config(self, filepath: str):
        """Save filter configuration to JSON file"""
        config = {
            'blocker_stages': [stage.to_dict() for stage in self.blocker_stages],
            'target_stage': self.target_stage.to_dict() if self.target_stage else None,
            'source_labels': self.source_labels
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    @classmethod
    def load_config(cls, filepath: str) -> 'LabelFilterEngine':
        """Load filter configuration from JSON file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            config = json.load(f)

        engine = cls()
        engine.source_labels = config.get('source_labels', [])

        # Load blocker stages
        for stage_data in config.get('blocker_stages', []):
            stage = FilterStage.from_dict(stage_data)
            engine.blocker_stages.append(stage)

        # Load target stage
        if config.get('target_stage'):
            engine.target_stage = FilterStage.from_dict(config['target_stage'])

        return engine

    def get_statistics(self) -> Dict[str, Any]:
        """Get filtering statistics"""
        results = self.get_stage_results()

        stats = {
            'source_count': len(results['source']),
            'final_count': len(results['final']),
            'removed_count': len(results['source']) - len(results['final']),
            'removal_percentage': (1 - len(results['final']) / len(results['source'])) * 100 if results['source'] else 0,
            'stage_counts': {
                name: len(labels)
                for name, labels in results.items()
            }
        }

        return stats


def create_example_config():
    """Create an example filter configuration"""
    engine = LabelFilterEngine()

    # Example labels (from Las Mercedes Heating-Cooling)
    engine.set_source_labels([
        "AHU01 North Supply Temperature AI_3000336",
        "AHU01 North Return Temperature AI_3000337",
        "Lighting Circuit 1-4-7 Status BI_3000065",
        "Fire Alarm BI_3000334",
        "Pump 1 Status BI_3000397",
        "Chiller 1 Alarm BI_3000442",
    ])

    # Blocker 1: Remove lighting
    bs1 = engine.add_blocker_stage('Bs1')
    bs1.add_filter('Lighting*', action='block', enabled=True)

    # Blocker 2: Remove alarms
    bs2 = engine.add_blocker_stage('Bs2')
    bs2.add_filter('*Alarm*', action='block', enabled=True)

    # Target: Include only temperature sensors
    ts = engine.set_target_stage('Ts')
    ts.add_filter('*Temperature*', action='include', enabled=True)

    return engine


if __name__ == '__main__':
    # Example usage
    print("="*80)
    print("LABEL FILTER ENGINE - Example")
    print("="*80)

    engine = create_example_config()

    print("\nSource labels:")
    for label in engine.source_labels:
        print(f"  - {label}")

    print("\nFilter stages:")
    for stage in engine.blocker_stages:
        print(f"\n{stage.name}:")
        for f in stage.filters:
            print(f"  - {f.action.upper()}: '{f.pattern}' (enabled: {f.enabled})")

    if engine.target_stage:
        print(f"\n{engine.target_stage.name}:")
        for f in engine.target_stage.filters:
            print(f"  - {f.action.upper()}: '{f.pattern}' (enabled: {f.enabled})")

    print("\n" + "="*80)
    print("Stage-by-stage results:")
    print("="*80)

    results = engine.get_stage_results()
    for stage_name, labels in results.items():
        print(f"\n{stage_name} ({len(labels)} labels):")
        for label in labels:
            print(f"  - {label}")

    print("\n" + "="*80)
    print("Statistics:")
    print("="*80)
    stats = engine.get_statistics()
    print(f"Source: {stats['source_count']} labels")
    print(f"Final: {stats['final_count']} labels")
    print(f"Removed: {stats['removed_count']} labels ({stats['removal_percentage']:.1f}%)")

    # Save configuration
    config_file = "example_filter_config.json"
    engine.save_config(config_file)
    print(f"\nConfiguration saved to: {config_file}")
