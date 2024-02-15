import streamlit as st
from streamlit_echarts import Map
from streamlit_echarts import st_echarts
from sqlalchemy import create_engine
import pandas as pd
import pycountry
import json
import random

st.set_page_config(page_title="Open Apparel Maps", page_icon=None, layout="wide")

engine = create_engine("sqlite:///data/sustainability.sqlite")
conn = engine.raw_connection()

def get_contributors():
    #with engine.raw_connection() as conn:
    df = pd.read_sql("SELECT contributor,contributor_id FROM t_oar_contributors WHERE contributor_id>0 ORDER BY contributor",con=conn)
    return df

def get_country_distribution():
    sql_query = "select iso_a3,COUNT(*) as num_facilities from t_oar_facilities group by iso_a3 order by num_facilities DESC;"

    #with engine.raw_connection() as conn:
    df =  pd.read_sql(sql_query,con=conn)
    return df

def build_country_distribution_piechart(df):
    option = {
        "tooltip": {"trigger":"item"},
        "series": [{
            "name": 'Country Code',
            "type": 'pie',
            "radius": ['20%', '45%'],
            "avoidLabelOverlap": True,
            "label": {
                "show": True,
                "color":"#FFF",
                "textBorderColor":"#FFF",
            },
            "emphasis": {
                "label": {"show": True, "fontSize": '40', "fontWeight": 'bold'
                }
            },
            "labelLine": { "show": False },
            "data": [
            ]
        }]
    }
    alldata = []
    for i,row in df.iterrows():
        c = pycountry.countries.get(alpha_3=row["iso_a3"])
        try:
            country = c.official_name
        except:
            country = c.name
        alldata.append({"value":row["num_facilities"],"name":country})
    option["series"][0]["data"] = alldata
    return option

def get_country_distribution_by_contributor(contributor_id):
    sql_query = f"select substring(facility_id,1,2) as iso_a2,facility_id from t_oar_contributor_facility_xref where contributor_id={contributor_id};"
    #with engine.raw_connection() as conn:
    df = pd.read_sql(sql_query,con=conn)

    sql_query = "select iso_a3,COUNT(*) as num_facilities from t_oar_facilities where id IN ({}) group by iso_a3 order by num_facilities DESC;".format(
        ",".join([f"'{f_id}'" for f_id in df.facility_id.values]))
    #with engine.raw_connection() as conn:
    df = pd.read_sql(sql_query,con=conn)
    return df

def draw_world_map_with_stats(df,dfCountries):
    with open("data/world.json", "r") as f:
        map = Map("world",json.loads(f.read()))

    option =  {
        "tooltip" : {
            "trigger": 'item',
        },
        "visualMap": {
            "min": 0,
            "max": 23804,
            "text":['High','Low'],
            "realtime": True,
            "calculable" : True,
            "color": ['orangered','yellow','lightskyblue']
        },
        "series" : [{
            "name": 'Supply Chain Location',
            "type": 'map',
            "map": 'world',
            "roam": True,
            "top": 60,
            "bottom": 60,
            "width": '100%',
            "data":[
                {"name" : 'Afghanistan', "value" : 28397.812},
            ]
        }]
    }

    option["visualMap"]["max"] = int(df.num_facilities.max())

    alldata = []
    for i,row in df.iterrows():
        country = pycountry.countries.get(alpha_3=row.iso_a3)
        if country.name == "Viet Nam": # Strange Quirk between pycountry and worldmap JSON
            alldata.append({"name":country.common_name,"value":int(row.num_facilities)})
        else:
            alldata.append({"name":country.name,"value":int(row.num_facilities)})

    option["series"][0]["data"] = alldata

    return map,option


def draw_top_locations():
    sql_query = "select iso_a3,COUNT(*) as num_facilities from t_oar_facilities group by iso_a3 order by num_facilities DESC;"
    #with engine.raw_connection() as conn:
    dfF = pd.read_sql(sql_query,con=conn)
    dfF["ratio"] = dfF.num_facilities/dfF.num_facilities.sum()
    dfF["rel_ratio"] = dfF.ratio/dfF.ratio.max()
    dfF = dfF[dfF.ratio>0.01]

    option = {
        "xAxis": {
            "type": 'category',
            "data": list(dfF.iso_a3.values),
            "axisLabel": {"rotate":90},
        },
        "yAxis": {
            "type": 'value',
        },
        "series": [{
            "data": [float(r) for r in dfF.rel_ratio.values],
            "type": 'bar'
        }]
    }

    return option


def draw_top_locations_relative(df):
    sql_query = "select iso_a3,COUNT(*) as num_facilities from t_oar_facilities group by iso_a3 order by num_facilities DESC;"
    #with engine.raw_connection() as conn:
    dfF = pd.read_sql(sql_query,con=conn)
    dfF["ratio"] = dfF.num_facilities/dfF.num_facilities.sum()
    dfF["rel_ratio"] = dfF.ratio/dfF.ratio.max()
    dfF = dfF[dfF.ratio>0.01]

    ddf = df[df.iso_a3.isin(dfF.iso_a3.values)].copy()
    ddf["ratio"] = ddf.num_facilities/ddf.num_facilities.sum()
    ddf["rel_ratio"] = ddf.ratio/ddf.ratio.max()
    #ddF = dfF[dfF.ratio>0.01]

    alldata = []
    for iso_a3 in dfF.iso_a3.values:
        xdf = ddf[ddf.iso_a3 == iso_a3]
        if len(xdf)>0:
            value = xdf.rel_ratio.values[0]/dfF[dfF.iso_a3 == iso_a3].rel_ratio.values[0]
        else:
            value = 0
        alldata.append({"iso_a3":iso_a3,"rel_ratio":value})
    xdf = pd.DataFrame(alldata)

    option = {
        "xAxis": {
            "type": 'category',
            "data": list(dfF.iso_a3.values),
            "axisLabel": {"rotate":90},
        },
        "yAxis": {
            "type": 'value',
        },
        "series": [{
            "data": [float(r) for r in dfF.rel_ratio.values],
            "type": 'bar'
        },{
            "data": [float(r) for r in xdf.rel_ratio.values],
            "type": 'bar'
        }]
    }

    return option,ddf,dfF


st.sidebar.markdown('Source of data: <a href="https://openapparel.org/facilities">Open Apparel</a>',unsafe_allow_html=True)

#with engine.raw_connection() as conn:
#    dfCountries = pd.read_sql("t_reference_countries",con=conn)

dfCountries = pd.read_sql("t_reference_countries",con=conn)

ddf = get_contributors()
if 'selection' not in st.session_state:
    st.session_state.selection = random.randrange(0,len(ddf))
selection = st.session_state.selection

contributor = st.sidebar.selectbox("Contributor",ddf.contributor.values,index=selection)
contributor_id = ddf[ddf.contributor==contributor].contributor_id.values[0]

df = get_country_distribution_by_contributor(contributor_id)

contributor_tc = contributor.title()

st.markdown(f"### Global Sourcing {contributor_tc}")


st.markdown("#### Countries")
st.write("Be aware these statistics show the number of supply chain relationships, not their monetary value.")
map,options = draw_world_map_with_stats(df,dfCountries)
st_echarts(options, map=map,height=400,width=600)

left_text, right_text = st.columns([1,1])

with left_text:
    st.markdown("#### Country Distribution")
    st.write("This shows the list-specific distribution of source countries. You can compare this to the global distribution in the side bar.")

with right_text:
    st.markdown("#### Relative Country Distrubution")
    st.write("""This puts this list's country distribution in relation to the global, average distribution. Values of 1 indicate similar list-specific distribution as global, values 
    greater than 1 indicate a preference for that country over an average.""")

left_chart, right_chart = st.columns([1,1])

options_specific = build_country_distribution_piechart(df)

with left_chart:
    a = st_echarts(options=options_specific,key="specific")
    options_pie = build_country_distribution_piechart(get_country_distribution())


options_top = draw_top_locations()
o,a,b = draw_top_locations_relative(df)

with right_chart:
    st_echarts(options=o,key="rel_top")


global_distribution = st.sidebar.empty()

with global_distribution.container():
    st.markdown("#### Global Distribution")
    b = st_echarts(options=options_pie,key="global_pie")

    st.markdown("#### Main Countries (Global)")
    c = st_echarts(options=options_top,key="global_top2")

