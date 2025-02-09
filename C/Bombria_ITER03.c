/*
 * Name: Jane Bombria
 * Class: CS 2060
 * Assignment: Iteration #3
 * OS: Mac (XCode)
 * Due date: 4/25/24
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h>
#include <ctype.h>

//Maximum length of a string
#define  STRING_LENGTH 80

// Folder path
#define FILE_PATH "/Users/janebombria/Desktop/RideShares/"
#define TEXT_FILE_FORMAT ".txt"

//Two dimensional array storage amounts for rows and columns of survey data
#define SURVEY_RIDER_ROWS 3
#define SURVEY_CATEGORIES 3

// login, sentinel values, and min factors
#define CORRECT_ID "id1"
#define CORRECT_PASSCODE "ABCD"
#define LOGIN_MAX_ATTEMPTS 3
#define SENTINAL_NEG1 -1
#define MIN_RAND_MINUTES_FACTOR 1.2
#define MAX_RAND_MINUTES_FACTOR 1.5

// MIN and MAX for rideshare
#define MIN 0.5
#define MAX 50

// Min and max for miles
#define MIN_MILES 1
#define MAX_MILES 100

// Min and mac for survey
#define SURVEY_MIN 1
#define SURVEY_MAX 5

const char *surveyCategories[SURVEY_CATEGORIES] = {"Safety", "Cleanliness", "Comfort"};

typedef struct rideShare{
    // variables
    double baseFare;
    double costPerMinute;
    double costPerMile;
    double minFlatRate;
    
    double currentMiles;
    
    // totals
    int riders;
    int currentSurveyEntries;
    int totalTime;
    double totalMiles;
    double totalFare;
    
    // arrays
    char organizationName[STRING_LENGTH];
    int survey[SURVEY_RIDER_ROWS][SURVEY_CATEGORIES];
    double surveyAverages[SURVEY_CATEGORIES];
    
    struct rideShare *nextPtr;
} RideShare;


// prototypes
bool adminLogIn(const char* correctID, const char* correctPass, unsigned int attempts);
void fgetsRemoveNewLine(char* stringPtr);
void setUpRideShare(RideShare *rideSharePtr, int min, int max);
bool scanDouble(char *stringPtr, double *validDoublePtr);
double getValidDoubleSent(double min, double max, int sentinel);
double getValidDouble(double min, double max);
void displayRidersMode(RideShare *rideSharePtr, size_t surveyRows, size_t surveyCategories, const char *surveyCategoriesPtr[]);
void getRatings(RideShare *rideSharePtr, const char *surveyCategories[], int min, int max, int maxCategories);
char getValidYN(char yes, char no);
double calculateFare(RideShare *rideSharePtr, double miles, int minutes);
void printCurrentCarResults(double miles, double fare, int min, int carCount);
void printBusinessSummary(RideShare *rideSharePtr);
void rideShare(RideShare *rideSharePtr);
void admin(RideShare *headRideSharePtr);
void printAverageCategoryData(RideShare *rideSharePtr, const char *surveyCategories[]);
void insertRideShare(RideShare ** headPtr, RideShare * toAddPtr);
void displayRideShareSetUp(RideShare *rideSharePtr);
void pickRideShare(RideShare *headPtr, RideShare **currentRideShare);
void pickRideShare(RideShare *headPtr, RideShare **currentRideShare);
void printToFile(RideShare *headPtr);


int main(void){
    RideShare headRideShare;
    
    admin(&headRideShare);
    puts("Exiting RideShare Program");
    printToFile(&headRideShare);
    
    return 0;
} // MAIN


/*
 * Admin Log In
 * Parameters: CorrectID, CorrectPass, allowed number of attempts
 * Returns: true if login was successful, false if login was unsuccessful
 */
bool adminLogIn(const char* correctID, const char* correctPass, unsigned int maxAttempts){
    int count = 1;
    char id[STRING_LENGTH];
    char *idPtr = id;
    char pass[STRING_LENGTH];
    char *passPtr = pass;
    
    bool logIn = false;
    bool isCorrectID = false;
    bool isCorrectPass = false;
    
    // get and check id and pass
    while((count <= maxAttempts) && !logIn){
        if(!isCorrectID){
            puts("Enter Admin ID: ");
            fgetsRemoveNewLine(idPtr);
            if(strcmp(idPtr, correctID) != 0){
                puts("Incorrect ID\n");
            }
            else{
                isCorrectID = true;
            }
        }
        if(!isCorrectPass){
            puts("Enter Admin Password: ");
            fgetsRemoveNewLine(passPtr);
            if(strcmp(passPtr, correctPass) != 0){
                puts("Incorrect Password\n");
            }
            else{
                isCorrectPass = true;
            }
        }
        count++;
    }
    // successfully logged in
    if(isCorrectID && isCorrectPass){
        puts("Logging in...");
        logIn = true;
    }
    return logIn;
}
/*
 * Returns user-entered string and removes new line character
 * Places null character at end
 * Parameters: Pointer to variable that will store string input
 * Return: No return, but the pointer is pass by reference and will directly change variable in other functions.
 */
void fgetsRemoveNewLine(char* stringPtr){
    fgets(stringPtr, STRING_LENGTH ,stdin);
    unsigned long stringLength = strlen(stringPtr);
    
    // replacing new line character
    stringPtr[stringLength - 1] = '\0';
}

/*
 * Initializes values in structure.
 * Parameters: Address to structure, min and max for inputs
 * Returns: No return, but since structure is pass by reference, it is impacted.
 */
void setUpRideShare(RideShare *rideSharePtr, int min, int max){
    // set up user-input varaibles
    puts("Set up ride share information");
    puts("Enter the base fare: ");
    rideSharePtr -> baseFare = getValidDouble(min, max);
    puts("Enter the cost per minute");
    rideSharePtr -> costPerMinute = getValidDouble(min, max);
    puts("Enter the cost per mile");
    rideSharePtr -> costPerMile = getValidDouble(min, max);
    puts("Enter min base fare");
    rideSharePtr -> minFlatRate = getValidDouble(min, max);
    puts("Enter rideshare name:");
    fgetsRemoveNewLine(rideSharePtr -> organizationName);
    
    // set totals to 0
    rideSharePtr -> totalFare = 0;
    rideSharePtr -> totalTime = 0;
    rideSharePtr -> totalMiles = 0;
    rideSharePtr -> riders = 0;
    rideSharePtr -> currentSurveyEntries = 0;
    rideSharePtr -> currentMiles = 0;
    rideSharePtr -> nextPtr = NULL;
    for(size_t columns = 0; columns < SURVEY_CATEGORIES; columns++){
        rideSharePtr -> surveyAverages[columns] = 0;
        }
}

/*
* Checks if the user input is actually a double
* Parameters: String pointer holding the user input, and the valid double pointer that will update if input is a  double
* Return: Returns a bool saying if the input is a double and updates validDouble since it was passed by reference
*/
    bool scanDouble(char *stringPtr, double *validDoublePtr){
        bool isValid = false;
        char *endPtr;
        double returnScan = 0;
        returnScan = strtod(stringPtr, &endPtr);
        if(returnScan != 0 && *endPtr == '\0'){
            isValid = true;
            *validDoublePtr = returnScan;
        }
        return isValid;
    }

// based on the code provided in Iteration 1 refactored code
/*
 * Checks if user input is a valid double or the sentinal value
 * Parameters: The limits for the input (min and max) and the sentinal
 * Return: Returns the valid double
 */
double getValidDoubleSent(double min, double max, int sentinel){
    bool isValid = false;
    double validDouble = 0;
    char tempString[STRING_LENGTH] = {0};
    char *tempStringPtr = &tempString;

    // get user input
    while((!isValid)){
        fgetsRemoveNewLine(tempStringPtr);
        isValid = scanDouble(tempString, &validDouble);
            
        // checks if in boundaries of min and max or is sentinal
        if(isValid){
            if((validDouble >= min && validDouble <= max) || validDouble == SENTINAL_NEG1){
                isValid = true;
            }
            else{
                printf("Not within %.1lf and %.1lf. Enter value again", min, max);
                isValid = false;
            }
        }
        else{
            puts("Error: Not an Integer number. Enter again.");
            isValid = false;
        }
    }
    return validDouble;
}

// based on the code provided in Iteration 1 refactored code
/*
* Checks if user input is a valid double
* Parameters: The limits for the input (min and max)
* Return: Returns the valid double
*/
double getValidDouble(double min, double max){
    bool isValid = false;
    double validDouble = 0;
    char tempString[STRING_LENGTH] = {0};
    char *tempStringPtr = &tempString;

    // get user input
    while((!isValid)){
        fgetsRemoveNewLine(tempStringPtr);
        isValid = scanDouble(tempString, &validDouble);

        // checks if in boundaries of min and max
        if(isValid){
            if(validDouble >= min && validDouble <= max){
                isValid = true;
            }
            else{
                printf("Not within %.1lf and %.1lf. Enter value again", min, max);
                isValid = false;
            }
        }
        else{
            puts("Error: Not an Integer number. Enter again.");
            isValid = false;
        }
    }
    return validDouble;
}

/*
 * Gets a valid number for rating between the min and max
 * Parameters: The rideShare pointer to get access to the survey 2D array, min and max for inputs, and the number of categories to put input into
 * Return: No return (void) but does initalize the surveyArray to inputs given.
 */
void getRatings(RideShare *rideSharePtr, const char *surveyCategories[],  int min, int max, int maxCategories){
    
    // gets ratings for all categories (collumns)
    for(size_t categories = 0; categories < maxCategories; categories++){
        int input = 0;
        puts("Enter your input for:");
        printf("%s \n",surveyCategories[categories]);
        input = (int)getValidDouble(min, max);
        rideSharePtr -> survey[rideSharePtr -> currentSurveyEntries][categories] = input;
        
        // add to averages for survey categories
        //rideSharePtr -> surveyAverages[categories] = input;
    }
    rideSharePtr -> currentSurveyEntries +=1;
}

/*
 * Prints the current results of the rideshare survey
 * Parameters: Pointer to the array with survey data, size of array's rows (number of entries) and collumns (categories)
 * Return: No return (void) but will print out the current results in array
 */
void displayRidersMode(RideShare *headRideSharePtr, size_t surveyRows, size_t surveyCategories, const char *surveyCategoriesPtr[]){
    RideShare *current = headRideSharePtr;
    
    while(current != NULL){
        printf("%s Ratings\n", current -> organizationName);
        puts("Survey Results");
        
            // if there were no riders
        if(current -> currentSurveyEntries <= 0){
            puts("No ratings currently");
        }
        else{
                // print each category
            for(size_t i = 0; i < SURVEY_CATEGORIES; i++) {
                printf("%s \t", surveyCategoriesPtr[i]);
            }
            puts("");
                // print data for each category
            for(size_t row = 0; row < current-> currentSurveyEntries; row++){
                printf("Survey %d: \t", row+1);
                for(size_t col = 0; col < surveyCategories; col++){
                    printf("%d \t", current ->survey[row][col]);
                }
                puts("");
            }
        }
        // move along linked list
        current = current->nextPtr;
    }
}

/*
 * Gets a valid yes or no answer
 * Parameters: Characters that represent yes and no.
 Note: For some reason the passed in characters change into '\0' after the fgetsNewLine function. However, if I do not include parameters into this function, my system aborts the program.
 * Return: Returns the valid answer (y/n).
 */
char getValidYN(char yes, char no){
    char answer = '\0';
    char *answerPtr = &answer;
    fgetsRemoveNewLine(answerPtr);
    
    // makes all input lowercase
    answer = tolower(answer);
    
    // checks if valid
    while(*answerPtr != 'y' && *answerPtr != 'n'){
        puts("You did not enter y/Y or n/N");
        fgetsRemoveNewLine(answerPtr);
        answer = tolower(answer);
    }
    return answer;
}

/*
 * Calculates the fare for this rider by doing the math.
 * Parameters: The
 */
//double calculateFare(double base, double minuteCost, double mileCost, double minRate , double miles, int minutes)
double calculateFare(RideShare *rideSharePtr, double miles, int minutes){
    double fareCharge = 0;
    
    // calculate fare and determine if it is equal or greater than minimum fare
    // if less than min fare, add more until it reaches min fare
    fareCharge = rideSharePtr -> baseFare + (minutes * rideSharePtr -> costPerMinute) + (miles * rideSharePtr -> costPerMile);
    if(fareCharge < rideSharePtr -> minFlatRate){
        double difference = rideSharePtr -> minFlatRate - fareCharge;
        fareCharge += difference;
    }
    return fareCharge;
} // calculateFare

/*
 * Prints the results from calculateFare for the current rider
 * Parameters: The miles, fare, and minutes taken for the current rider (carCount)
 * Returns: No return (void), but does print results.
 */
void printCurrentCarResults(double miles, double fare, int min, int carCount){
    puts("Current Ride Information");
    puts("Rider \t Number of Miles \t Number of Minutes \t Ride Fare Amount");
    printf("%d \t\t\t",carCount);
    printf("%.1lf \t\t\t\t", miles);
    printf("%d \t\t\t\t", min);
    printf("%.2lf \n", fare);
} // printCurrentCarResults

/*
 * Calculates the averages of the survey categories and stores in surveyAverages array
 * Parameter: Pointer to rideShare to have access to arrays
 * Return: No return(void), but does update surveyAverages array
 */
void calculateCategoryAverages(RideShare *headRideSharePtr){
    RideShare *current = headRideSharePtr;
    // calculates average from each category for each ride share
    // top to bottom and left to right
    while(current != NULL){
        for(size_t columns = 0; columns < SURVEY_CATEGORIES; columns++){
            int total = 0;
            for(size_t rows = 0; rows < current -> riders; rows++){
                total+= current -> survey[rows][columns];
            }
            double average = ((double)total/current -> riders);
            current -> surveyAverages[columns] = average;
        }
        current = current -> nextPtr;
    }
}

/*
 * Prints the averages of the surveyAverage array
 * Parameters: Pointer to rideShare to have access to arrays, pointer to survey catergories to have access to names
 * Returns: No return(void), but does print out information
 */
void printAverageCategoryData(RideShare *headRideSharePtr, const char *surveyCategories[]){
    RideShare *current = headRideSharePtr;
    
    while(current != NULL){
            // print category names
        puts("Category Rating Average");
            // checks if there were actually surveys entered
        if(current->surveyAverages[0] != 0){
            printf("%s \n", current -> organizationName);
            for(size_t categories = 0; categories < SURVEY_CATEGORIES; categories++){
                printf("%d. %s \t",categories+1 ,surveyCategories[categories]);
            }
            puts(""); // blank line
            
                // print data for each category
            for(size_t categories = 0; categories < SURVEY_CATEGORIES; categories++){
                printf("%.2lf \t", current -> surveyAverages[categories]);
            }
        }
        else{
            puts("There were no surveys entered.");
        }
        puts("");
        current = current->nextPtr;
    }
}


/*
 * Prints the current totaled data in the rideShare
 * Parameters: Takes the pointer to the rideShare to have access to all total data.
 */
void printBusinessSummary(RideShare *headRideSharePtr){
    RideShare *current = headRideSharePtr;
    while(current != NULL){
        puts("Ride Share Business Summary");
        printf("%s \n", current -> organizationName);
        if(current->riders != 0){
            puts("Riders \t Number of Miles \t Number of Minutes \t Ride Fare Amount");
            printf("%d \t\t\t", current -> riders);
            printf("%.2lf \t\t\t\t", current -> totalMiles);
            printf("%d \t\t\t\t", current -> totalTime);
            printf("%.2lf", current -> totalFare);
            puts("");
            
        }
        else{
            puts("There were no rides. \n");
        }
        current = current-> nextPtr;
        puts(""); // blank line
    }
}// printBusinessSummary

/*
 * Runs the rideShare
 * Parameters: Pointer to rideShare to have access to all data
 * Returns: No return (print), but does print and run entire rideshare
 */
void rideShare(RideShare *headRideSharePtr){
    char yn = '\0';
    bool isRunning = true;
    double minMinutes = 0;
    double maxMinutes = 0;
    double miles = 0;
    int minutes = 0;
    int surveyEntries = 0;
    
        // enter while when running
    while(isRunning){
            // choose ride share and store in variable
        RideShare *currentRideSharePtr = NULL;
        pickRideShare(headRideSharePtr, &currentRideSharePtr);
        
            // display welcome and current surveys for all rideshares
        displayRidersMode(headRideSharePtr, SURVEY_RIDER_ROWS, SURVEY_CATEGORIES, surveyCategories);
        puts(""); // blank line
        printf("Welcome to %s. We can only provide services for rides from 1 to 100 miles. \n", currentRideSharePtr -> organizationName);
        
            // ask for miles input
        puts("Enter the number of miles to your destination:");
        miles = getValidDoubleSent(MIN_MILES, MAX_MILES, SENTINAL_NEG1);
        currentRideSharePtr -> currentMiles = miles;
        
            // if miles is not sentinal, calculate fare
        if(miles != SENTINAL_NEG1){
                // calculates minutes and fare
            minMinutes = MIN_RAND_MINUTES_FACTOR * miles;
            maxMinutes = MAX_RAND_MINUTES_FACTOR * miles;
            if (miles != 1){
                minutes = rand() % ((int)maxMinutes - (int)minMinutes) + (int)minMinutes;
            }
                // deals with minutes if user enters 1 mile
                //(without causes minutes to be in the thousands for 1 miles)(taken from my iteration 1)
            else{
                minutes = 1;
            }
            double fareCharge = calculateFare(currentRideSharePtr, miles, minutes);
            currentRideSharePtr -> riders += 1;
            currentRideSharePtr -> currentMiles = 0;
            printCurrentCarResults(miles, fareCharge, minutes, currentRideSharePtr -> riders);
            
                // add totals to structure
            currentRideSharePtr -> totalFare += fareCharge;
            currentRideSharePtr -> totalTime += minutes;
            currentRideSharePtr -> totalMiles += miles;
            puts("Do you want to share your rideshare experience? (y/n)");
            yn = getValidYN('y','n');
            
                // enter ratings for rideshare
            if(yn == 'y'){
                puts("We want to know how your experience was on your ride today. Using the rating system 1 to 5 enter your rating for each category:");
                getRatings(currentRideSharePtr, surveyCategories, SURVEY_MIN, SURVEY_MAX, SURVEY_CATEGORIES);
                surveyEntries++;
            }
            else{
                puts("Thanks for riding with us.");
            }
        }
            // if sentinal was entered, and admin is correct, shut off ride share and print business summary
        else{
            bool adminLogin = adminLogIn(CORRECT_ID, CORRECT_PASSCODE, LOGIN_MAX_ATTEMPTS);
            if(adminLogin){
                puts(""); //blank line
                printBusinessSummary(headRideSharePtr);
                calculateCategoryAverages(headRideSharePtr);
                printAverageCategoryData(headRideSharePtr, surveyCategories);
                puts(""); //blank line
                isRunning = false;
            }
        }
    }
}

/*
 * Prompts for admin log in and deals with admin tasks
 * Parameters: RideShare pointer to have access to data
 * Return: No return (void), but does print and run admin side of rideshare.
 */
void admin(RideShare *headRideSharePtr){
    // log in
    bool adminLogin = adminLogIn(CORRECT_ID, CORRECT_PASSCODE, LOGIN_MAX_ATTEMPTS);
    
    // run ONLY after successful login. If not successful, end program
    while(adminLogin){
        // initialize variables for head rideshare
        setUpRideShare(headRideSharePtr, MIN, MAX);
        puts(""); //blank line
        
        // add another rideshare to the linked list
        puts("Add another rideshare? (y/n)");
        char rsAnswer = getValidYN('y', 'n');
        while(rsAnswer == 'y'){
            // create blank new rideShare and intitialize
            RideShare *newRideShare = malloc(sizeof(RideShare));
            if(newRideShare != NULL){
                setUpRideShare(newRideShare, MIN, MAX);
                insertRideShare(&headRideSharePtr, newRideShare);
                puts("Add another rideshare? (y/n)");
                rsAnswer = getValidYN('y', 'n');
            }
        }
        // print ride share variables
        displayRideShareSetUp(headRideSharePtr);
        
        // log out and go to rideShare
        adminLogin = false;
        rideShare(headRideSharePtr);
    }
}
/*
 * Inserts a node into the rideshare, alphabetically
 * Parameters: The pointer to the pointer to the head and a the pointer of the node you want to add to the list
 * Return: Returns the updated linked list (head). If the node to add was added to the front, replaced the address in the headPtr pointer to the address of the added node. If added to the middle or back, updates the nextPtr of the node before the node added.
 */
void insertRideShare(RideShare ** headPtr, RideShare * toAddPtr){
    // set up pointers to walk along list
    RideShare *previousPtr = NULL;
    RideShare *currentPtr = *headPtr;
    
    // if spot is not found, move along linked list to find the spot
    while(currentPtr != NULL && strncmp(currentPtr->organizationName, toAddPtr->organizationName, STRING_LENGTH) <= 0){
        previousPtr = currentPtr;
        currentPtr = currentPtr->nextPtr;
    }
    
    // make new node the head
    if(previousPtr == NULL){
        toAddPtr-> nextPtr = *headPtr;
        *headPtr = toAddPtr;
    }
    // add node to middle or end
    else{
        previousPtr-> nextPtr = toAddPtr;
        toAddPtr-> nextPtr = currentPtr;
    }
}

/*
 * Displays the variables set up in the setUpRideShare function for the entire linked list
 * Parameter: The pointer to the head node of the linked list. The head holds the entire linked list.
 * Return: No return (void), but does print the variables and values stored in each node of the rideshare
 */
void displayRideShareSetUp(RideShare *headRideSharePtr){
    RideShare *currentPtr = headRideSharePtr;
    while(currentPtr != NULL){
        printf("%s \n", currentPtr -> organizationName);
        printf("Base Fare: %.1lf \n", currentPtr -> baseFare);
        printf("Cost per Minute: %.1lf \n", currentPtr -> costPerMinute);
        printf("Cost per Mile: %.1lf \n", currentPtr -> costPerMile);
        printf("Base Min Fare: %.1lf \n", currentPtr -> minFlatRate);
        puts("");       // blank line
        currentPtr = currentPtr->nextPtr;
    }
    puts("Exiting Admin Mode \n");
}

/*
 * Traverses the linked list to find the node with the entered rideshare name
 * Parameters: The pointer to the head node of the rideshare and the pointer to the pointer of the selected ride share
 * Return: Returns the updated currentRideShare pointer, which will store the address of the currently selected rideshare
 */
void pickRideShare(RideShare *headPtr, RideShare **currentRideShare){
    bool found = false;
    RideShare *currentPtr = headPtr;
    char nameToFind[STRING_LENGTH];
    while(!found){
        // get input to find rideshare and make it lower case
        puts("Enter the name of a rideshare");
        fgetsRemoveNewLine(&nameToFind);
        unsigned long inputLength = strlen(nameToFind);
        for(int i = 0; i < inputLength; i++){
            nameToFind[i] = tolower(nameToFind[i]);
        }
        
        // go through linked list
        while(currentPtr != NULL && !found){
            // make organization name lowercase for comparison
            unsigned long orgNameLength = strlen(currentPtr-> organizationName);
            char compareOrganization[STRING_LENGTH] = {0};
            for(int i = 0; i < orgNameLength; i++){
                compareOrganization[i] = tolower(currentPtr->organizationName[i]);
            }
            
            // compare strings
            if(strncmp(nameToFind, compareOrganization, STRING_LENGTH) == 0){
                found = true;
                *currentRideShare = currentPtr;
            }
            else{
                currentPtr = currentPtr-> nextPtr;
            }
            
            // if not found, print error
            if(!found && currentPtr == NULL){
                puts("Organization not found");
            }
        }
        // reset current pointer if this organization name was not found
        currentPtr = headPtr;
    }
}

/*
 * Takes all the information from each rideshare and prints the information into seperate files
 * Parameter: The pointer to the head node of the linked list to have access to all the information in the linked list
 * Return: No return(void), but will create new files in the designated area on computer
 */
void printToFile(RideShare *headPtr){
    FILE *cfPtr = NULL;
    char currentFile [STRING_LENGTH] = {0};
    RideShare *current = headPtr;
    
    
    // go through entire rideshare and print data to files
    while(current != NULL){
        // set up file name
        strncpy(&currentFile, FILE_PATH, STRING_LENGTH);
        
        // stores the rideshare name in a string (char array)
        char rideShareName[STRING_LENGTH] = {0};
        unsigned long orgNameLength = strlen(current-> organizationName);
        for(int i = 0; i < orgNameLength; i++){
            rideShareName[i] = current->organizationName[i];
        }
        
        // add file name and text file format to file path array
        strncat(currentFile, rideShareName, STRING_LENGTH);
        strncat(currentFile, TEXT_FILE_FORMAT, STRING_LENGTH);
        
        // replace all spaces with _
        unsigned long fileNameLength = strlen(currentFile);
        for(int i = 0; i < fileNameLength; i++){
            if(currentFile[i] == ' '){
                currentFile[i] = '_';
            }
        }
        
        
    // fopen opens the file. Exit the program if unable to create the file
    if ((cfPtr = fopen(currentFile, "w")) == NULL) {
        puts("File could not be opened");
    }
    else {
        // write rideshare info into file with fprintf
            //fprintf(cfPtr, "%d %s %.2f\n", account, name, balance);
        fprintf(cfPtr, "%s Summary Report \n", current -> organizationName);
        if(current->riders != 0){
            fprintf(cfPtr, "Riders \t Number of Miles \t Number of Minutes \t Ride Fare Amount \n");
            fprintf(cfPtr, "%d \t", current -> riders);
            fprintf(cfPtr, "%.2lf \t", current -> totalMiles);
            fprintf(cfPtr, "%d \t", current -> totalTime);
            fprintf(cfPtr, "%.2lf \n", current -> totalFare);
        }
        else{
            fprintf(cfPtr, "There were no rides.");
        }
        
        // printf survey averages
        // print category names and data for each category
        fprintf(cfPtr, "Category Rating Average \n");
        if(current->surveyAverages[0] != 0){
            fprintf(cfPtr, "%s \n", current -> organizationName);
            for(size_t categories = 0; categories < SURVEY_CATEGORIES; categories++){
                fprintf(cfPtr, "%d. %s \t",categories+1 ,surveyCategories[categories]);
            }
            fprintf(cfPtr, ""); // new line in file
            for(size_t categories = 0; categories < SURVEY_CATEGORIES; categories++){
                fprintf(cfPtr, "%.2lf \t", current -> surveyAverages[categories]);
            }
        }
        else{
            fprintf(cfPtr, "There were no surveys entered.");
        }
    }
    fclose(cfPtr); // close current file
    current = current -> nextPtr;
    }
}
