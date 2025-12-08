import pandas as pd

# Read the taxpayers CSV
df = pd.read_csv('data/taxpayers.csv')

print("Current columns:", list(df.columns))

# Check if we have both address columns
if 'Principal Place of Business </br>Address' in df.columns and 'Address' in df.columns:
    print("\nFound both address columns!")
    
    # Copy data from the full column name to 'Address' where Address is NaN
    df['Address'] = df.apply(
        lambda row: row['Principal Place of Business </br>Address'] 
        if pd.isna(row['Address']) and not pd.isna(row['Principal Place of Business </br>Address'])
        else row['Address'],
        axis=1
    )
    
    # Drop the long column name
    df = df.drop(columns=['Principal Place of Business </br>Address'])
    
    print("Merged address data into 'Address' column and removed duplicate")
    
    # Save back
    df.to_csv('data/taxpayers.csv', index=False)
    print("\nUpdated taxpayers.csv saved!")
    print("New columns:", list(df.columns))
else:
    print("\nNo duplicate address columns found")
