# Track Times Research

When I ran track in high school, my local newspaper put out a "Top 50 Athletes" for each sport. After 4 years of running, 2 All-State titles, 3 County Championships, and several All-Counties... I never appeared on this list. I looked at it puzzled sometimes, "I've never lost to this guy in a race, how is he on it and not me." So the statistician inside of me wanted to find a real way to measure who the best track and field athletes were; is a 10.99 in the 100m more impressive than a 1:59 in the 800m?

Of course, both are fast high school times, but comparing them isn't simple. Each event has its own field, with a different number of runners, a different spread of times, and a different limit on how fast a person can go. A tenth of a second is huge in the 100m and almost nothing in the 800m.

## The idea

Instead of asking "how fast is this time?", I ask "how rare is it?"

Every performance gets a **return period**: roughly, "a time this fast shows up once in every N athletes." A return period has no units (in some sense, it's just a count of people), so a sprint and a distance race can finally be compared directly.

## Looking at the front of the pack

Most runners in any event finish somewhere in the middle. That's where most of the data is, but it's not where the interesting question is. If I want to know how rare a 10.31 is, the runners at 12.5 don't tell me much.

So I only model the **tail**: the small group of athletes at the very front of each event.

To do this, I use **extreme value theory**, a branch of statistics built for questions about the most extreme values: floods, record heat waves, and, it turns out, fast runners. For each event, I:

1. Collect results from state ranking lists on [athletic.net](https://www.athletic.net).
2. Pick a cutoff that separates the fastest runners from everyone else.
3. Fit a curve to the times past that cutoff, describing how quickly performances get rarer as they get faster.
4. Score any time by reading off how rare it is.

## Events

100m, 200m, 400m, 800m, and the metric mile.

"The mile" turned out to be trickier than I expected. Depending on the state, high schoolers run the 1500m, the 1600m, or a full mile. Those are different distances, so each one gets its own model.

## Files

scrape.py is the original scraping file I used. It can only do one at a time after a series of manual inputs.
scrapeAll.py is the file I will be now using for most of my scraping. 
