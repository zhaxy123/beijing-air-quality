import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import json
import numpy as np
import time
from datetime import datetime

class BeijingAirQualityStreamlitApp:
    def __init__(self, hourly_data_path=None):
        self.hourly_data_path = hourly_data_path
        self.available_dates = []
        self.available_hours = []
        self.df_hourly = None
        self.beijing_geojson = None
        self.df_stations = None
        self.load_data()
        
    def load_data(self):
        try:
            with open('北京市.json', 'r', encoding='utf-8') as f:
                self.beijing_geojson = json.load(f)
        except FileNotFoundError:
            st.warning("未找到北京市.json文件，将创建无边界的地图")
            self.beijing_geojson = None
        
        self.stations_data = {
            'name': ['东城东四', '东城天坛', '西城官园', '西城万寿西宫', '朝阳奥体中心', '朝阳农展馆', 
                     '海淀万柳', '海淀四季青', '丰台小屯', '丰台云岗', '石景山古城', '石景山老山',
                     '昌平镇', '昌平南邵', '定陵(对照点)', '延庆夏都', '延庆石河营', '怀柔镇',
                     '怀柔新城', '密云镇', '密云新城', '平谷镇', '平谷新城', '顺义新城', '顺义北小营',
                     '通州永顺', '通州东关', '大兴黄村', '大兴旧宫', '亦庄开发区', '京东南区域点',
                     '门头沟双峪', '门头沟三家店', '房山良乡', '房山燕山'],
            'lon': [116.417, 116.407, 116.339, 116.352, 116.397, 116.461, 
                    116.287, 116.23052, 116.25528, 116.146, 116.176, 116.20764,
                    116.234, 116.27603, 116.22, 115.972, 116.00138, 116.628,
                    116.6018, 116.832, 116.85152, 117.118, 117.0854, 116.655, 116.6853,
                    116.67503, 116.6996, 116.404, 116.47456, 116.506, 116.78437,
                    116.106, 116.09122, 116.136, 115.96916],
            'lat': [39.929, 39.886, 39.929, 39.878, 39.982, 39.937, 
                    39.987, 40.03, 39.87694, 39.824, 39.914, 39.90886,
                    40.217, 40.21651, 40.292, 40.453, 40.46327, 40.328,
                    40.3118, 40.37, 40.4088, 40.143, 40.15353, 40.127, 40.16087,
                    39.93435, 39.9131, 39.718, 39.78284, 39.795, 39.63606,
                    39.937, 39.96926, 39.742, 39.76419],
            'region': ['城六区']*12 + ['西北部']*5 + ['东北部']*8 + ['东南部']*6 + ['西南部']*4
        }
        
        if self.hourly_data_path:
            encodings = ['gbk', 'gb2312', 'utf-8', 'latin1', 'iso-8859-1']
            for encoding in encodings:
                try:
                    self.df_hourly = pd.read_csv(self.hourly_data_path, encoding=encoding)
                    self.preprocess_data()
                    break
                except Exception:
                    continue
        
        self.df_stations = pd.DataFrame(self.stations_data)

    def preprocess_data(self):
        if self.df_hourly is None:
            return
            
        if 'datetime' in self.df_hourly.columns:
            self.df_hourly['datetime'] = pd.to_datetime(self.df_hourly['datetime'])
            self.df_hourly['date'] = self.df_hourly['datetime'].dt.date.astype(str)
            self.df_hourly['hour'] = self.df_hourly['datetime'].dt.hour
        else:
            time_col = self.df_hourly.columns[0]
            try:
                self.df_hourly['datetime'] = pd.to_datetime(self.df_hourly[time_col])
                self.df_hourly['date'] = self.df_hourly['datetime'].dt.date.astype(str)
                self.df_hourly['hour'] = self.df_hourly['datetime'].dt.hour
            except:
                self.df_hourly['date'] = '2025-11-01'
                self.df_hourly['hour'] = 0
        
        self.available_dates = sorted(self.df_hourly['date'].unique())
        self.available_hours = sorted(self.df_hourly['hour'].unique())
    
    def get_aqi_level(self, aqi):
        if pd.isna(aqi): return '无数据'
        if aqi <= 50: return '优'
        elif aqi <= 100: return '良'
        elif aqi <= 150: return '轻度污染'
        elif aqi <= 200: return '中度污染'
        elif aqi <= 300: return '重度污染'
        else: return '严重污染'
    
    def get_aqi_color(self, aqi):
        if pd.isna(aqi): return 'gray'
        if aqi <= 50: return 'green'
        elif aqi <= 100: return 'yellow'
        elif aqi <= 150: return 'orange'
        elif aqi <= 200: return 'red'
        elif aqi <= 300: return 'purple'
        else: return 'maroon'

    def get_region_center(self, region_name):
        region_centers = {
            '城六区': [39.9042, 116.4074], '西北部': [40.216, 116.234],
            '东北部': [40.37, 116.832], '东南部': [39.718, 116.404],
            '西南部': [39.742, 116.136]
        }
        return region_centers.get(region_name, [39.9042, 116.4074])

    def create_base_map(self, selected_regions):
        if selected_regions and '全部' not in selected_regions and len(selected_regions) == 1:
            center = self.get_region_center(selected_regions[0])
            zoom_start = 10
        else:
            center = [40.3, 116.4074]
            zoom_start = 8
            
        beijing_map = folium.Map(
            location=center,
            zoom_start=zoom_start,
            tiles=None  # 无地图背景
        )
        
        if self.beijing_geojson:
            region_colors = {
                '城六区': '#FF6B6B', '西北部': '#4ECDC4', '东北部': '#45B7D1',
                '东南部': '#96CEB4', '西南部': '#FFEAA7'
            }
            
            region_mapping = {
                '东城区': '城六区', '西城区': '城六区', '朝阳区': '城六区',
                '海淀区': '城六区', '丰台区': '城六区', '石景山区': '城六区',
                '昌平区': '西北部', '延庆区': '西北部', '怀柔区': '西北部',
                '密云区': '东北部', '平谷区': '东北部', '顺义区': '东北部',
                '通州区': '东南部', '大兴区': '东南部', '亦庄': '东南部',
                '门头沟区': '西南部', '房山区': '西南部'
            }
            
            for feature in self.beijing_geojson['features']:
                properties = feature.get('properties', {})
                district_name = (properties.get('name') or properties.get('NAME') or 
                               properties.get('区域') or properties.get('region') or '未知')
                region_name = region_mapping.get(district_name, '未知')
                color = region_colors.get(region_name, '#CCCCCC')
                
                folium.GeoJson(
                    feature,
                    style_function=lambda feature, color=color: {
                        'fillColor': color, 'color': 'white',
                        'weight': 2, 'fillOpacity': 0.3
                    },
                    tooltip=f"{district_name} - {region_name}"
                ).add_to(beijing_map)
        
        # 添加图例到地图上
        self.add_legends_to_map(beijing_map)
        
        return beijing_map

    def add_legends_to_map(self, map_obj):
        """在地图上直接添加图例"""
        # 区域图例
        region_legend_html = '''
        <div style="
            position: fixed; 
            top: 10px; 
            left: 10px; 
            width: 180px;
            background: white;
            border: 2px solid grey;
            border-radius: 5px;
            padding: 10px;
            font-size: 12px;
            z-index: 9999;
        ">
        <h4 style="margin:0 0 8px 0; text-align:center;">区域分布</h4>
        <div style="display: flex; align-items: center; margin: 3px 0;">
            <div style="width:15px; height:15px; background:#FF6B6B; margin-right:5px; border:1px solid #666;"></div>
            <span>城六区</span>
        </div>
        <div style="display: flex; align-items: center; margin: 3px 0;">
            <div style="width:15px; height:15px; background:#4ECDC4; margin-right:5px; border:1px solid #666;"></div>
            <span>西北部</span>
        </div>
        <div style="display: flex; align-items: center; margin: 3px 0;">
            <div style="width:15px; height:15px; background:#45B7D1; margin-right:5px; border:1px solid #666;"></div>
            <span>东北部</span>
        </div>
        <div style="display: flex; align-items: center; margin: 3px 0;">
            <div style="width:15px; height:15px; background:#96CEB4; margin-right:5px; border:1px solid #666;"></div>
            <span>东南部</span>
        </div>
        <div style="display: flex; align-items: center; margin: 3px 0;">
            <div style="width:15px; height:15px; background:#FFEAA7; margin-right:5px; border:1px solid #666;"></div>
            <span>西南部</span>
        </div>
        </div>
        '''
        
        # AQI图例
        aqi_legend_html = '''
        <div style="
            position: fixed; 
            top: 200px; 
            left: 10px; 
            width: 150px;
            background: white;
            border: 2px solid grey;
            border-radius: 5px;
            padding: 10px;
            font-size: 12px;
            z-index: 9999;
        ">
        <h4 style="margin:0 0 8px 0; text-align:center;">AQI等级</h4>
        <div style="display: flex; align-items: center; margin: 3px 0;">
            <div style="width:12px; height:12px; background:green; border-radius:50%; margin-right:5px;"></div>
            <span>优 (0-50)</span>
        </div>
        <div style="display: flex; align-items: center; margin: 3px 0;">
            <div style="width:12px; height:12px; background:yellow; border-radius:50%; margin-right:5px;"></div>
            <span>良 (51-100)</span>
        </div>
        <div style="display: flex; align-items: center; margin: 3px 0;">
            <div style="width:12px; height:12px; background:orange; border-radius:50%; margin-right:5px;"></div>
            <span>轻度污染 (101-150)</span>
        </div>
        <div style="display: flex; align-items: center; margin: 3px 0;">
            <div style="width:12px; height:12px; background:red; border-radius:50%; margin-right:5px;"></div>
            <span>中度污染 (151-200)</span>
        </div>
        <div style="display: flex; align-items: center; margin: 3px 0;">
            <div style="width:12px; height:12px; background:purple; border-radius:50%; margin-right:5px;"></div>
            <span>重度污染 (201-300)</span>
        </div>
        <div style="display: flex; align-items: center; margin: 3px 0;">
            <div style="width:12px; height:12px; background:maroon; border-radius:50%; margin-right:5px;"></div>
            <span>严重污染 (>300)</span>
        </div>
        </div>
        '''
        
        map_obj.get_root().html.add_child(folium.Element(region_legend_html))
        map_obj.get_root().html.add_child(folium.Element(aqi_legend_html))

    def add_station_markers(self, map_obj, selected_levels, selected_regions, selected_date, selected_hour):
        if self.df_hourly is None:
            return
            
        time_data = self.df_hourly[
            (self.df_hourly['date'] == selected_date) & 
            (self.df_hourly['hour'] == selected_hour)
        ]
        
        if time_data.empty:
            return
            
        time_row = time_data.iloc[0]
        
        for idx, row in self.df_stations.iterrows():
            station_name = row['name']
            station_region = row['region']
            
            if '全部' not in selected_regions and station_region not in selected_regions:
                continue
            
            if station_name not in time_row:
                continue
                
            aqi_value = time_row[station_name]
            aqi_level = self.get_aqi_level(aqi_value)
            
            if '全部' not in selected_levels and aqi_level not in selected_levels:
                continue
            
            color = self.get_aqi_color(aqi_value)
            
            folium.CircleMarker(
                location=[row['lat'], row['lon']],
                radius=8,
                popup=f"<b>{station_name}</b><br>区域: {station_region}<br>时间: {selected_date} {selected_hour}:00<br>AQI: {aqi_value}<br>等级: {aqi_level}",
                tooltip=f"{station_name} - AQI: {aqi_value}",
                color=color, fill=True, fillColor=color, fillOpacity=0.7, weight=2
            ).add_to(map_obj)

    def create_filtered_map(self, selected_date, selected_hour, selected_levels, selected_regions):
        map_obj = self.create_base_map(selected_regions)
        self.add_station_markers(map_obj, selected_levels, selected_regions, selected_date, selected_hour)
        return map_obj

def main():
    st.set_page_config(page_title="北京空气质量可视化系统",  layout="wide")
    st.title("北京空气质量可视化系统")
    
    if 'app' not in st.session_state:
        st.session_state.app = BeijingAirQualityStreamlitApp('project_data/aqi_hourly.csv')
    
    app = st.session_state.app
    
    with st.sidebar:
        st.header("筛选设置")
        
        # 时间选择
        datetime_input = st.text_input(
        "输入日期时间 (格式: 2025110120)\n数据范围[2022-01-01 - 2025-11-01]",
        value=f"{app.available_dates[-1].replace('-', '')}{app.available_hours[-1]:02d}" if app.available_dates and app.available_hours else "2025110100"
    )
            
        # 解析输入的日期时间
        if datetime_input and len(datetime_input) == 10:
            try:
                input_date = f"{datetime_input[:4]}-{datetime_input[4:6]}-{datetime_input[6:8]}"
                input_hour = int(datetime_input[8:10])
                
                # 检查输入是否在可用范围内
                if input_date in app.available_dates and input_hour in app.available_hours:                        
                    selected_date = input_date
                    selected_hour = input_hour
                else:
                    st.warning("输入的日期时间不在数据范围内，使用默认时间")
                    selected_date = app.available_dates[-1] if app.available_dates else "2025-11-01"
                    selected_hour = app.available_hours[-1] if app.available_hours else 0                
            except:
                st.warning("日期时间格式错误，使用默认时间")
                selected_date = app.available_dates[-1] if app.available_dates else "2025-11-01"
                selected_hour = app.available_hours[-1] if app.available_hours else 0
        else:
            # 默认使用最新时间
            selected_date = app.available_dates[-1] if app.available_dates else "2025-11-01"
            selected_hour = app.available_hours[-1] if app.available_hours else 0
        
        
        regions = ['全部', '城六区', '西北部', '东北部', '东南部', '西南部']
        levels = ['全部', '优', '良', '轻度污染', '中度污染', '重度污染', '严重污染']

        def handle_multiselect_change(current_selection, previous_selection):
            if current_selection != previous_selection:
                if '全部' in current_selection and len(current_selection) > 1:
                    return ['全部']
                elif '全部' not in current_selection and len(current_selection) > 0:
                    if '全部' in current_selection:
                        current_selection.remove('全部')
                return current_selection
            return previous_selection

        if 'selected_regions' not in st.session_state:
            st.session_state.selected_regions = ['全部']
        selected_regions = st.multiselect("选择区域", regions, default=st.session_state.selected_regions)
        st.session_state.selected_regions = handle_multiselect_change(selected_regions, st.session_state.selected_regions)

        if 'selected_levels' not in st.session_state:
            st.session_state.selected_levels = ['全部']
        selected_levels = st.multiselect("选择污染等级", levels, default=st.session_state.selected_levels)
        st.session_state.selected_levels = handle_multiselect_change(selected_levels, st.session_state.selected_levels)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("空气质量地图")
        if hasattr(app, 'df_hourly') and app.df_hourly is not None:
            map_obj = app.create_filtered_map(selected_date, selected_hour, selected_levels, selected_regions)
            st_folium(map_obj, width=800, height=600)
        else:
            st.error("数据加载失败，请检查数据文件")

    with col2:
        st.subheader("数据统计")
        
        # 当前时间显示
        st.info(f"**当前时间:**\n{selected_date} {selected_hour:02d}:00")
        
        # 监测站点数量统计
        total_stations = len(app.df_stations)
        
        # 根据区域筛选计算显示的站点数量
        if '全部' in selected_regions:
            display_stations = total_stations
        else:
            display_stations = len([station for station in app.df_stations['region'] if station in selected_regions])
        
        st.metric("总监测站点数", total_stations)
        st.metric("当前显示站点数", display_stations)
        
        # 筛选结果
        st.markdown("### 筛选结果")
        st.write(f"**选中区域:** {', '.join(selected_regions)}")
        st.write(f"**污染等级:** {', '.join(selected_levels)}")
    
    
    
if __name__ == "__main__":
    main()