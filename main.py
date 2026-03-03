import pandas as pd
import os
import re
import glob
import gspread
from gspread_dataframe import set_with_dataframe
import spot_downloader
import config
import logging

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger(__name__)

def extract(data_dir: str = config.DATA_DIR) -> tuple:
    """Extract Logs from Gmail for today."""
    os.makedirs(data_dir, exist_ok=True)
    logger.info("Extract: Loading Data...")
    gmail_service = spot_downloader.get_gmail_service()
    if gmail_service:
        logger.info("Checking Gmail for new files...")
        spot_downloader.download_attachments(gmail_service, output_dir=data_dir, folder_name=config.GMAIL_LABEL)
    try:
        prefixes = config.FILE_PREFIXES
        all_filepaths = []
        for p in prefixes:
            paths = glob.glob(os.path.join(data_dir, f'{p}*.xls'))
            if not paths:
                logger.warning(f"No files found for prefix: {p} in {data_dir}. Skipping date extraction from this prefix.")
                all_filepaths.append([])
            else:
                all_filepaths.append(paths)

        # Check if we have at least one file to work with
        if not any(all_filepaths):
            logger.error("No valid spreadsheet files found for any prefix.")
            return None, None, None, None, None

        # Load dataframes safely
        dfs = []
        for i, paths in enumerate(all_filepaths):
            if paths:
                try:
                    df = pd.read_excel(paths[0], header=5)
                    dfs.append(df)
                    logger.info(f"Loaded file: {os.path.basename(paths[0])}")
                except Exception as e:
                    logger.error(f"Error reading file {paths[0]}: {e}")
                    dfs.append(pd.DataFrame()) # Append empty if failed
            else:
                dfs.append(pd.DataFrame())

        def extract_date_from_filename(filepath):
            if not filepath: return ""
            basename = os.path.basename(filepath)
            match = re.search(r'\d{4}-\d{2}-\d{2}', basename)
            return match.group(0) if match else ""

        # Use the first available file for the date
        first_valid_path = next((p[0] for p in all_filepaths if p), None)
        date = extract_date_from_filename(first_valid_path)
        
        return dfs[0], dfs[1], dfs[2], dfs[3], date
        
    except Exception as e:
        logger.exception(f"Unexpected error during extract: {e}")
        raise


def transform(df2, df4, df5, df9, date) -> pd.DataFrame:
    """Transform data."""
    logger.info("Transform: Cleaning Data...")
    try:
        df2 = df2[['…','Act.Time','Descripcion','Ext. Copy Number','Advertiser Id']]
        df4 = df4[['…','Act.Time','Descripcion','Ext. Copy Number','Advertiser Id']]
        df5 = df5[['…','Act.Time','Descripcion','Ext. Copy Number','Advertiser Id']]
        df9 = df9[['…','Act.Time','Descripcion','Ext. Copy Number','Advertiser Id']]
        
        def filter_spots(df):
            advertiser_mask = df['Advertiser Id'].isin(config.ADVERTISER_IDS)
            special_mask = df['Descripcion'] == config.SPECIAL_SPOT
            return df[advertiser_mask | special_mask].copy()

        Spot2 = filter_spots(df2)
        Spot4 = filter_spots(df4)
        Spot5 = filter_spots(df5)
        Spot9 = filter_spots(df9)
        
        regional_id = config.ADVERTISER_IDS[-1]  # Last ID is used for time override
        for spot in [Spot2, Spot4, Spot5, Spot9]:
            spot.loc[spot['Advertiser Id'] == regional_id, 'Act.Time'] = spot['…']
        

        # Append date to Act.Time. Convert Act.Time to datetime to avoid errors.
        Spot2['Act.Time'] = date + " " + Spot2['Act.Time'].astype(str)
        Spot4['Act.Time'] = date + " " + Spot4['Act.Time'].astype(str)
        Spot5['Act.Time'] = date + " " + Spot5['Act.Time'].astype(str)
        Spot9['Act.Time'] = date + " " + Spot9['Act.Time'].astype(str)

        for spot in [Spot2, Spot4, Spot5, Spot9]:
            spot.loc[spot['Descripcion'] == config.SPECIAL_SPOT, 'Ext. Copy Number'] = spot['Descripcion']

        Spot2 = Spot2.drop(columns=['…', 'Descripcion','Advertiser Id'])
        Spot4 = Spot4.drop(columns=['…', 'Descripcion','Advertiser Id'])
        Spot5 = Spot5.drop(columns=['…', 'Descripcion','Advertiser Id'])
        Spot9 = Spot9.drop(columns=['…', 'Descripcion','Advertiser Id'])

        Spot2 = Spot2.rename(columns={'Ext. Copy Number': 'Spot', 'Act.Time': 'Time'})
        Spot4 = Spot4.rename(columns={'Ext. Copy Number': 'Spot', 'Act.Time': 'Time'})
        Spot5 = Spot5.rename(columns={'Ext. Copy Number': 'Spot', 'Act.Time': 'Time'})
        Spot9 = Spot9.rename(columns={'Ext. Copy Number': 'Spot', 'Act.Time': 'Time'})
        
        def adjust_last_protection(df):
            if len(df) > 1 and df.iloc[-1]['Spot'] == config.SPECIAL_SPOT:
                prev_time = pd.to_datetime(df.iloc[-2]['Time'])
                new_time = prev_time + pd.Timedelta(seconds=30)
                df.at[df.index[-1], 'Time'] = str(new_time)
            return df

        Spot2 = adjust_last_protection(Spot2)
        Spot4 = adjust_last_protection(Spot4)
        Spot5 = adjust_last_protection(Spot5)
        Spot9 = adjust_last_protection(Spot9)

        def assign_shift(df):
            # Convert to datetime to extract time safely
            dt = pd.to_datetime(df['Time'])
            
            # Calculate numerical HHMM representation (e.g., 6:30 -> 630, 12:45 -> 1245)
            hm = dt.dt.hour * 100 + dt.dt.minute
            
            # Default value
            df['Turno'] = 'Fuera de horario'
            
            # Assign shifts using loc
            df.loc[(hm >= 600) & (hm < 1240), 'Turno'] = 'Mañana'
            df.loc[(hm >= 1240) & (hm < 1900), 'Turno'] = 'Tarde'
            df.loc[(hm >= 1900) | (hm <= 115), 'Turno'] = 'Noche'
            
            return df

        Spot2 = assign_shift(Spot2)
        Spot4 = assign_shift(Spot4)
        Spot5 = assign_shift(Spot5)
        Spot9 = assign_shift(Spot9)

        return Spot2, Spot4, Spot5, Spot9

    except KeyError as e:
        logger.error(f"Missing expected column: {e}")
        raise

    except AssertionError:
        logger.error("Data validation failed")
        raise

    except Exception as e:
        logger.exception(f"Unexpected error during transform: {e}")
        raise


def load(Spot2, Spot4, Spot5, Spot9):
    """Load data to Google Sheets."""
    logger.info("Connecting to Google Sheets...")
    
    # Check if credentials exist as file, otherwise spot_downloader handles env vars
    # but gspread needs a specific file or dict. 
    # We'll use spot_downloader's logic to ensure files exist.
    spot_downloader.get_gmail_service() # This ensures credentials.json is created if in env
    
    if os.path.exists('credentials.json'):
        gc = gspread.service_account(filename='credentials.json')
    else:
        logger.error("credentials.json not found. Cannot upload to Google Sheets.")
        return

    # Open the Google Sheet by its name (or you can use gc.open_by_key('SHEET_ID'))
    sh = gc.open(config.GOOGLE_SHEET_NAME) 

    # Helper function to upload a DataFrame to a specific sheet
    def upload_to_sheet(sh, df, sheet_name):
        try:
            worksheet = sh.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            # If the sheet does not exist, create it
            worksheet = sh.add_worksheet(title=sheet_name, rows="100", cols="20")
     
        worksheet.clear() # Clear the sheet before uploading the new data
        set_with_dataframe(worksheet, df)
        logger.info(f"Sheet '{sheet_name}' updated in Google Sheets.")
 
    logger.info("Uploading data to Google Sheets...")
    # Upload the 4 DataFrames to their respective sheets
    upload_to_sheet(sh, Spot2, 'Spot2')
    upload_to_sheet(sh, Spot4, 'Spot4')
    upload_to_sheet(sh, Spot5, 'Spot5')
    upload_to_sheet(sh, Spot9, 'Spot9')
 
    logger.info("All data was successfully uploaded to Google Sheets.")


def main():
    logger.info("ETL Process Started")
    df2,df4, df5, df9, date = extract()
    if df2 is None:
        logger.warning("No data found to process. Exiting...")
        return
        
    Spot2, Spot4, Spot5, Spot9 = transform(df2, df4, df5, df9, date)
    load(Spot2, Spot4, Spot5, Spot9)
    logger.info("ETL Process Completed")

if __name__ == '__main__':
    main()