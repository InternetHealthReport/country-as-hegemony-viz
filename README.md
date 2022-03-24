# Visualising AS Hegemony per country

This is code that takes AS Hegemony data from the Internet Health Report together with AS Links (via RIPEstat)
to create GDF files that can be visualised by Gephi.

# How to use

Install the country AS Hegemony code from the Internet Health Report ( https://github.com/InternetHealthReport/country-as-hegemony ):

```
pip install country-as-hegemony
```

Then edit the doit.sh script in this repo, to point at that code. 

This doit.sh script also has variables for the date and country to run this on. Change these accordingly.

Run the doit.sh script, which will generate a GDF file.
