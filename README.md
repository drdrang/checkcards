Checkcards is set of scripts for querying the Naperville Public Library about the status of items checked out and on hold for all the members of a family. [This blog post][1] describes the motivation for the scripts and how they work.

![Sample email on iPhone](http://www.leancrew.com/all-this/images/library-email-iphone.png)

To use the scripts, you'll have to make these changes:

* In `checkcards.py`, the section starting on Line 8 will have to be personalized with your email addresses and library card information.

    * `mailFrom` is the sender's email address
    * `mailTo` is the recipient's email address; it can be the same as the sender's
    * `cardList` is a list of Python dictionary entries, each of which consists of
    
        * `patron`: the cardholder's name, which can be a first name of a nickname—it isn't used to log in.
        * `code`: the barcode number on the front of the library card
        * `pin`: the cardholder's PIN
    
    I keep my settings in a file called `personal.py`, which isn't included in the repository.
    
* In `checkcards`, Line 3 needs the full path to `checkcards.py`.

* In `com.leancrew.checkcards.plist`, the ProgramArguments entry needs the full path to `checkcards`, and the StartCalendarInterval entry should be set to whenever you want the program to run.

The `com.leancrew.checkcards.plist` file is needed if you plan to use OS X's `launchd` system to run `checkcards` at scheduled times. Put it in your `~/Library/LaunchAgents/` folder (which you may need to create) and run

    launchctl load ~/Library/LaunchAgents/com.leancrew.checkcards.plist

from the Terminal. You can check that it loaded correctly by running

    launchctl list | grep leancrew


[1]: http://www.leancrew.com/all-this/2009/03/library-loan-tracking-again/
