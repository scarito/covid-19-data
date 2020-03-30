Python code to load / clean up the JHU COVID-19 dataset.

To get started:
1. Clone the repository
2. Run ./update_jhu_data.sh to download and apply fixes to the dataset.
3. Load the data:

        import covid_19_data
	all_data = covid_19_data.LoadAllJhuData()
	timeseries = covid_19_data.CreateTimeseries(all_data)

4. Look at the Example.ipynb notebook for some example plots.
