# Canadian Call Schedule generator

Making call schedules is hard! I wanted to come up with a way that was fair for everyone. So I made a Call Schedule generator.

In Nova Scotia, call schedules must adhere to certain rules:
<<<<<<< HEAD
1. Residents cannot be on call more than 7 days per 28 days 
2. Residents cannot be on call two consecutive weekends
3. Residents cannot be on call two consecutive days
=======
    1. Residents cannot be on call more than 7 days per 28 days 
    2. Residents cannot be on call two consecutive weekends
    3. Residents cannot be on call two consecutive days
>>>>>>> 3d414d318e88a8f1df88492ac4fc7f99951135d2

However, even when there are valid call schedules, not all schedules are made equal! For instance, I think that senior residents should do less call. But, spreading out call shifts is preferable to doing 1:2 call of the time. To capture this idea, I describe each call schedule as having a "strain score." 

My approach was to bootstrap call schedules. The algorithm works as follows:
<<<<<<< HEAD
1. Load the resident names and availability from a `json` file
2. Assign residents to days within the rotation period
3. Check to see if the schedule is valid. If valid, then compute the schedule's strain score
4. Report the schedule with the lowest strain score
=======
    1. Load the resident names and availability from a `json` file
    2. Assign residents to days within the rotation period
    3. Check to see if the schedule is valid. If valid, then compute the schedule's strain score
    4. Report the schedule with the lowest strain score
>>>>>>> 3d414d318e88a8f1df88492ac4fc7f99951135d2

Dependencies:
    1. `tqdm` : used for making the progress bar pretty

Most of the code should be pretty self explanatory. Enjoy!
