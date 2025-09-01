# LVM Segments Visualizer

## Project Overview

A Python tool that analyzes and visualizes Linux LVM (Logical Volume Manager) segment distribution across physical disks. The tool provides both live system analysis and file-based analysis with comprehensive graphical representations and text summaries.

## Current Features

- **Live System Analysis**: Direct analysis of the current system's LVM configuration using `pvdisplay -m --units M`
- **File-based Analysis**: Parse saved `pvdisplay` output from any system
- **Dual Visualization**:
  - Stacked bar chart showing space usage by Physical Volume
  - Linear segment distribution chart showing physical layout
- **RAID Support**: Properly handles RAID1 volumes (_rimage_ and _rmeta_ components)
- **Sorted Display**: Physical Volumes sorted alphabetically for consistent output
- **Comprehensive Text Summary**: Usage statistics by PV and global totals
- **High-resolution Output**: PNG charts saved at 300 DPI

## Technical Stack

- **Language**: Python 3
- **Dependencies**: 
  - `matplotlib` - For chart generation
  - `numpy` - For numerical operations
  - `subprocess` - For executing system commands
  - `re` - For parsing pvdisplay output
- **Input Format**: Output of `sudo pvdisplay -m --units M`
- **Output Formats**: 
  - Console text summary
  - PNG visualization files
  - Interactive matplotlib display

## File Structure

```
lvm_visualizer.py          # Main script
pvdisplay_sample.txt       # Sample data file (user's actual LVM config)
README.md                  # User documentation
CLAUDE.md                  # This context file
```

## Current Usage Patterns

```bash
# Default: Live analysis
python3 lvm_visualizer.py

# Explicit live analysis
python3 lvm_visualizer.py --live

# File analysis
python3 lvm_visualizer.py data_file.txt

# Help
python3 lvm_visualizer.py --help
```

## Code Architecture

### Core Classes

- **`LVMAnalyzer`**: Main class containing all analysis logic
  - `parse_pvdisplay_output()`: Parse live command output
  - `parse_pvdisplay_from_data()`: Parse file content
  - `assign_colors()`: Color assignment for LVs
  - `create_visualization()`: Generate matplotlib charts
  - `plot_pv_overview()`: Stacked bar chart
  - `plot_segments_detail()`: Linear segment view
  - `print_summary()`: Text statistics output

### Key Functions

- `analyze_from_file()`: File-based analysis workflow
- `run_live_analysis()`: Live system analysis workflow  
- `show_help()`: Help text display
- Main argument parsing and routing

## Data Processing Logic

1. **Input Parsing**: Regex-based parsing of pvdisplay output to extract:
   - PV information (name, VG, size, PE details)
   - Physical segment ranges and their LV assignments
   - Free space segments

2. **Data Structure**: Internal representation using dictionaries:
   ```python
   pvs[pv_name] = {
       'vg': 'volume_group_name',
       'size': float,  # MB
       'pe_size': float,  # MB
       'segments': [
           {'start': int, 'end': int, 'lv': 'lv_name', 'size': float}
       ]
   }
   ```

3. **Visualization Generation**:
   - Color assignment using predefined palette
   - Matplotlib figure with dual subplots
   - Data aggregation for stacked views
   - Sorting by PV name for consistency

## Sample Data Context

The current sample data represents a real LVM configuration with:
- **6 Physical Volumes**: nvme0n1p3, sda1, sdb, sdc1, sdd1, sdd2
- **2 Volume Groups**: vg0, purelvm  
- **Multiple LV Types**: Linear volumes, RAID1 arrays with metadata
- **Complex Fragmentation**: Video LV spread across multiple PVs
- **Mixed Usage**: Some PVs 100% full, others with significant free space

## Development Guidelines

- **Language**: All user-facing text in English
- **Sorting**: Always sort PVs alphabetically for consistent output
- **Error Handling**: Comprehensive try/catch with helpful error messages
- **Dependencies**: Minimize external dependencies, stick to standard + matplotlib/numpy
- **Output**: Support both console and file output modes
- **Performance**: Handle large LVM configurations efficiently

## Potential Enhancements

### High Priority
- **Export Formats**: CSV/JSON data export
- **Interactive Charts**: Hover tooltips, clickable segments
- **Performance Monitoring**: Track LV performance metrics if available
- **Configuration Validation**: Warn about potential issues (fragmentation, full PVs)

### Medium Priority  
- **Historical Analysis**: Compare multiple snapshots over time
- **Recommendations**: Suggest optimization strategies
- **Multiple Systems**: Batch analysis of multiple systems
- **Advanced RAID**: Support for RAID5/6, stripping configurations

### Low Priority
- **GUI Interface**: Tkinter or web-based interface
- **Real-time Monitoring**: Continuous monitoring mode
- **Integration**: Plugin for existing monitoring systems
- **Custom Themes**: Color scheme customization

## System Requirements

- **OS**: Linux with LVM2 installed
- **Python**: 3.6+ 
- **Privileges**: sudo access for live analysis
- **Memory**: Minimal - handles large LVM configs efficiently
- **Display**: Optional - can run headless and save to files

## Testing Scenarios

- **Live System**: Test on various LVM configurations
- **File Analysis**: Parse different pvdisplay formats and edge cases
- **Large Configurations**: Systems with 10+ PVs, complex RAID setups
- **Error Cases**: Invalid files, missing permissions, corrupted data
- **Edge Cases**: Empty VGs, unused PVs, exotic LV types

## Known Limitations

- **LVM Version**: Assumes standard LVM2 pvdisplay format
- **Units**: Currently hardcoded to MB, could support other units
- **RAID Types**: Optimized for RAID1, other RAID types may need adjustment
- **Metadata**: Limited parsing of LVM metadata beyond basic segment info

## Integration Points

- **Monitoring Systems**: Easy to integrate with Nagios, Zabbix, etc.
- **Automation**: Suitable for automated reporting scripts  
- **Documentation**: Can generate reports for system documentation
- **Troubleshooting**: Helps visualize LVM layout issues

This tool is production-ready but has room for enhancements in interactivity, export options, and advanced LVM feature support.
