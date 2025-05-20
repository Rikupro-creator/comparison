import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
import requests
import os

# Set page configuration
st.set_page_config(
    page_title="Country Metric Comparison Tool",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add title and description
st.title("Country Metric Comparison Tool")
st.markdown("Compare two countries based on metrics from Our World in Data")

# Function to load dataset - with better error handling and alternative paths
@st.cache_data
def load_dataset():
    try:
        # Try the original file path
        file_path = "C:\\Users\\Michael Njuguna\\Downloads\\owid_data.xlsx"
        
        # Check if file exists
        if os.path.exists(file_path):
            df = pd.read_excel(file_path, sheet_name="Sheet1")
        else:
            # If in streamlit cloud or file not available, ask for file upload
            st.warning("Local file not found. Please upload your data file.")
            uploaded_file = st.file_uploader("Upload OWID data Excel file", type=['xlsx'])
            
            if uploaded_file is not None:
                df = pd.read_excel(uploaded_file, sheet_name="Sheet1")
            else:
                return None
                
        # Clean the dataframe
        df = df.dropna(subset=["data link full column names"])
        return df
    except Exception as e:
        st.error(f"Error loading dataset: {e}")
        return None

# Function to fetch country data with better error handling
@st.cache_data
def fetch_country_data(url):
    """Fetches data from the given OWID CSV link."""
    try:
        # Add timeout and user-agent to avoid blocking
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = pd.read_csv(BytesIO(response.content))
            return data
        else:
            st.error(f"Failed to fetch data: HTTP {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None

# Added fallback country list in case API fails
FALLBACK_COUNTRIES = [
    "United States", "China", "India", "Russia", "Germany", 
    "United Kingdom", "France", "Japan", "Brazil", "Canada",
    "Australia", "Italy", "Spain", "Mexico", "South Korea", 
    "Indonesia", "Turkey", "Saudi Arabia", "Argentina", "South Africa"
]

# Load the main dataset
df = load_dataset()

if df is not None:
    # Extract metrics
    metrics = df["metric"].dropna().astype(str).unique().tolist()
    
    # Setup sidebar for selecting data
    st.sidebar.header("Select Data to Compare")
    
    # Try to get countries from the first dataset with better error handling
    countries = []
    with st.sidebar:
        with st.spinner("Loading country list..."):
            try:
                # Get the first valid URL from the dataset
                for i, url in enumerate(df["data link full column names"]):
                    if not pd.isna(url) and url.strip() != "":
                        st.info(f"Trying to load country list from dataset {i+1}...")
                        first_data = fetch_country_data(url)
                        if isinstance(first_data, pd.DataFrame) and "Entity" in first_data.columns:
                            countries = sorted(first_data["Entity"].unique().tolist())
                            st.success(f"Successfully loaded {len(countries)} countries!")
                            break
                
                # If still no countries, use fallback
                if not countries:
                    st.warning("Could not load country list from data sources. Using a default list.")
                    countries = FALLBACK_COUNTRIES
            except Exception as e:
                st.error(f"Error loading countries: {e}")
                st.info("Using default country list instead.")
                countries = FALLBACK_COUNTRIES
    
    if countries:
        # Select countries
        col1, col2 = st.sidebar.columns(2)
        with col1:
            country_a = st.selectbox("Select First Country", countries, index=0)
        with col2:
            # Set default to a different country if possible
            default_idx = 1 if len(countries) > 1 else 0
            country_b = st.selectbox("Select Second Country", countries, index=default_idx)
        
        # Select metric
        selected_metric = st.sidebar.selectbox("Select a Metric", metrics, index=0)
        
        # Add a button to trigger comparison
        if st.sidebar.button("Compare Countries", type="primary", use_container_width=True):
            st.subheader(f"Comparing {country_a} vs {country_b}: {selected_metric}")
            
            # Create a progress container
            progress_container = st.empty()
            progress_container.info("Fetching data...")
            
            # Get the data link for the selected metric
            if selected_metric in df['metric'].values:
                link = df[df["metric"] == selected_metric]["data link full column names"].values[0]
                progress_container.info(f"Downloading data for {selected_metric}...")
                
                data = fetch_country_data(link)
                
                if data is None:
                    progress_container.error("Failed to fetch data. Please check the URL or your internet connection.")
                else:
                    progress_container.info("Processing data...")
                    
                    # Check required columns
                    if "Entity" not in data.columns or "Year" not in data.columns:
                        progress_container.error("Invalid data format - missing Entity or Year columns")
                    else:
                        # Filter data for selected countries
                        country_a_data = data[data["Entity"] == country_a]
                        country_b_data = data[data["Entity"] == country_b]
                        
                        if country_a_data.empty:
                            progress_container.error(f"No data available for {country_a}")
                        elif country_b_data.empty:
                            progress_container.error(f"No data available for {country_b}")
                        else:
                            # Find metric column
                            metric_columns = [col for col in data.columns if selected_metric.lower() in col.lower()]
                            if not metric_columns:
                                # Try other columns as fallback
                                potential_columns = [col for col in data.columns if col not in ["Entity", "Year", "Code"]]
                                if potential_columns:
                                    metric_column = potential_columns[0]
                                else:
                                    progress_container.error(f"Could not find data column for {selected_metric}")
                                    st.stop()
                            else:
                                metric_column = metric_columns[0]
                            
                            # Find latest years with data
                            latest_year_a = country_a_data["Year"].max()
                            latest_year_b = country_b_data["Year"].max()
                            
                            country_a_latest = country_a_data[country_a_data["Year"] == latest_year_a]
                            country_b_latest = country_b_data[country_b_data["Year"] == latest_year_b]
                            
                            # Get latest values
                            value_a = country_a_latest[metric_column].values[0] if not country_a_latest.empty else None
                            value_b = country_b_latest[metric_column].values[0] if not country_b_latest.empty else None
                            
                            # Calculate statistics
                            country_a_stats = {
                                'max': country_a_data[metric_column].max(),
                                'min': country_a_data[metric_column].min(),
                                'mean': country_a_data[metric_column].mean(),
                                'max_year': country_a_data.loc[country_a_data[metric_column].idxmax(), 'Year'] 
                                    if not pd.isna(country_a_data[metric_column].idxmax()) else None,
                                'min_year': country_a_data.loc[country_a_data[metric_column].idxmin(), 'Year']
                                    if not pd.isna(country_a_data[metric_column].idxmin()) else None
                            }
                            
                            country_b_stats = {
                                'max': country_b_data[metric_column].max(),
                                'min': country_b_data[metric_column].min(),
                                'mean': country_b_data[metric_column].mean(),
                                'max_year': country_b_data.loc[country_b_data[metric_column].idxmax(), 'Year']
                                    if not pd.isna(country_b_data[metric_column].idxmax()) else None,
                                'min_year': country_b_data.loc[country_b_data[metric_column].idxmin(), 'Year']
                                    if not pd.isna(country_b_data[metric_column].idxmin()) else None
                            }
                            
                            if pd.isna(value_a) or pd.isna(value_b):
                                progress_container.error("Missing data values for one or both countries")
                            else:
                                # Clear progress message
                                progress_container.empty()
                                
                                # Display current values with metrics
                                st.subheader("Current Values")
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.metric(
                                        label=f"{country_a} ({latest_year_a})", 
                                        value=f"{value_a:,.2f}"
                                    )
                                with col2:
                                    st.metric(
                                        label=f"{country_b} ({latest_year_b})", 
                                        value=f"{value_b:,.2f}", 
                                        delta=f"{value_b - value_a:,.2f}"
                                    )
                                
                                # Display statistical summary
                                st.subheader("Statistical Summary")
                                stat_col1, stat_col2, stat_col3 = st.columns(3)
                                
                                with stat_col1:
                                    st.metric(label=f"{country_a} Maximum", value=f"{country_a_stats['max']:,.2f}", 
                                            help=f"Year: {int(country_a_stats['max_year'])}" if country_a_stats['max_year'] is not None else "N/A")
                                    st.metric(label=f"{country_b} Maximum", value=f"{country_b_stats['max']:,.2f}", 
                                            help=f"Year: {int(country_b_stats['max_year'])}" if country_b_stats['max_year'] is not None else "N/A")
                                
                                with stat_col2:
                                    st.metric(label=f"{country_a} Minimum", value=f"{country_a_stats['min']:,.2f}", 
                                            help=f"Year: {int(country_a_stats['min_year'])}" if country_a_stats['min_year'] is not None else "N/A")
                                    st.metric(label=f"{country_b} Minimum", value=f"{country_b_stats['min']:,.2f}", 
                                            help=f"Year: {int(country_b_stats['min_year'])}" if country_b_stats['min_year'] is not None else "N/A")
                                
                                with stat_col3:
                                    st.metric(label=f"{country_a} Mean", value=f"{country_a_stats['mean']:,.2f}")
                                    st.metric(label=f"{country_b} Mean", value=f"{country_b_stats['mean']:,.2f}")
                                
                                # Display bar chart
                                st.subheader("Bar Chart Comparison")
                                fig1, ax1 = plt.subplots(figsize=(10, 6))
                                bars = ax1.bar(
                                    [country_a, country_b], 
                                    [value_a, value_b], 
                                    color=['#3498db', '#e74c3c'], 
                                    width=0.6
                                )
                                
                                # Add value labels
                                for bar, value in zip(bars, [value_a, value_b]):
                                    height = bar.get_height()
                                    ax1.text(
                                        bar.get_x() + bar.get_width() / 2,
                                        height * 1.01,
                                        f"{value:,.2f}",
                                        ha='center',
                                        va='bottom',
                                        fontweight='bold'
                                    )
                                
                                ax1.set_xlabel("Country", fontsize=12)
                                ax1.set_ylabel(metric_column, fontsize=12)
                                ax1.set_title(f"Current {selected_metric} Values", fontsize=14)
                                ax1.grid(axis='y', linestyle='--', alpha=0.7)
                                plt.tight_layout()
                                st.pyplot(fig1)
                                
                                # Time series line plot
                                st.subheader("Historical Trend Comparison")
                                
                                # Prepare time series data
                                country_a_time = country_a_data.dropna(subset=[metric_column])
                                country_b_time = country_b_data.dropna(subset=[metric_column])
                                
                                if not country_a_time.empty and not country_b_time.empty:
                                    # Create line plot
                                    fig2, ax2 = plt.subplots(figsize=(12, 6))
                                    
                                    # Plot data
                                    ax2.plot(country_a_time["Year"], country_a_time[metric_column], 
                                            marker='o', linestyle='-', color='#3498db', label=country_a)
                                    ax2.plot(country_b_time["Year"], country_b_time[metric_column], 
                                            marker='s', linestyle='-', color='#e74c3c', label=country_b)
                                    
                                    # Format plot
                                    ax2.set_xlabel("Year", fontsize=12)
                                    ax2.set_ylabel(metric_column, fontsize=12)
                                    ax2.set_title(f"Historical Trend of {selected_metric}", fontsize=14)
                                    ax2.grid(True, linestyle='--', alpha=0.7)
                                    ax2.legend(loc='best')
                                    
                                    # Try to set reasonable y-axis limits
                                    combined_min = min(country_a_stats['min'], country_b_stats['min'])
                                    combined_max = max(country_a_stats['max'], country_b_stats['max'])
                                    range_buffer = (combined_max - combined_min) * 0.1
                                    ax2.set_ylim(combined_min - range_buffer, combined_max + range_buffer)
                                    
                                    # Format x-axis ticks
                                    plt.xticks(rotation=45)
                                    
                                    plt.tight_layout()
                                    st.pyplot(fig2)
                                else:
                                    st.warning("Insufficient time series data available for one or both countries")
                                
                                # Show the raw data
                                st.subheader("Raw Data")
                                
                                # Combine data for both countries
                                combined_data = pd.concat([
                                    country_a_data[["Entity", "Year", metric_column]],
                                    country_b_data[["Entity", "Year", metric_column]]
                                ]).sort_values(["Entity", "Year"])
                                
                                st.dataframe(combined_data.reset_index(drop=True))
                                
                                st.success("Comparison completed successfully!")
            else:
                st.error(f"Invalid metric: {selected_metric}")
        else:
            # Show instructions when first loading
            st.info("👈 Select countries and a metric, then click 'Compare Countries' to see the comparison")
            
            # Show example of available metrics
            st.subheader("Available Metrics")
            st.dataframe(pd.DataFrame({"Metrics": metrics}))
    else:
        st.error("No countries available. Please check your data source.")
else:
    # Alternative flow if dataset loading fails
    st.error("Failed to load the dataset. Please upload your data file.")
    
    # Add file uploader directly on the main page
    uploaded_file = st.file_uploader("Upload OWID Excel File", type=['xlsx'])
    
    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file, sheet_name="Sheet1")
            df = df.dropna(subset=["data link full column names"])
            
            # Show preview of the data
            st.success("File uploaded successfully! Data preview:")
            st.dataframe(df.head())
            
            st.info("Please refresh the page to continue with the loaded data.")
        except Exception as e:
            st.error(f"Error processing uploaded file: {e}")
            st.info("Please make sure your Excel file contains a 'Sheet1' with a 'data link full column names' and 'metric' columns.")

# Add footer
st.sidebar.markdown("---")
st.sidebar.caption("Data source: Our World in Data")