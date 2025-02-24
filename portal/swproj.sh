#!/bin/bash

if [ "$1" = "--help" ]; then
    echo
    echo "./projenv.sh Project environment switcher script, utopia-cms 2025. @anibalpacheco"
    echo "Switches local settings files between current project and another given by argument"
    echo
    echo "Usage: $0                       # to show current project (if it can be detected)"
    echo "Usage: $0 <project>             # to switch from current project to the project given by argument"
    echo "Usage: $0 <current> [--check]   # only to check if current (given by argument) is the current project"
    echo
    exit 0
fi

# Define the default list of projects
declare -a projects=(
    "utopiacms"
)
# extends the list using other projects loaded in root project's .env (if any)
if [ -f ../.env ]; then
    source ../.env
    for project in ${PROJECTS[@]}; do
        projects+=($project)
    done
fi

# Define the sets of files
declare -a files=(
    "_"
    "_test_"
    "_migration_"
)

# Function to check if files are identical
files_identical() {
    diff "$1" "$2" >/dev/null 2>&1
    return $?
}

if [ "$2" = "--check" ]; then
    check=true
else
    check=false
fi

find_first_diff() {
    for project in "${projects[@]}"; do
        all_conditions_met=true
        for file in "${files[@]}"; do
            compare1="local${file}settings.py"
            compare2="local_${project}${file}settings.py"
            if ! files_identical "$compare1" "$compare2"; then
                all_conditions_met=false
                break
            fi
        done
        if $all_conditions_met; then
            if $check; then
                exit 0
            else
                break
            fi
        fi
    done
}

if [ $# -eq 0 ]; then
    find_first_diff
    if $all_conditions_met; then
        echo -e "\033[32m$project\033[0m"
        echo "Use --help to show usage"
        exit 0
    else
        echo -e "\033[31mNo current project detected\033[0m, use '<project> --check' to see diffs with another project"
        exit 1
    fi
fi

swto=$1

if $check; then
    projects=($swto)
    find_first_diff
else
    find_first_diff
    if $all_conditions_met && [ "$swto" = "$project" ]; then
        echo -e "\033[32mAlready in $project\033[0m"
        exit 0
    fi
    if ! [[ " ${projects[@]} " =~ " $swto " ]]; then
        echo -e "\033[31mInvalid project: $swto\033[0m"
        exit 1
    fi
fi

firsttwo() {
    echo
    echo "First two lines of the current local_settings.py are:"
    head -n 2 "local_settings.py"
    echo
}

# Perform actions if all conditions are met
if $all_conditions_met; then
    echo "Current project environment detected is '$swto'"
    for file in "${files[@]}"; do
        cp "local_${swto}${file}settings.py" "local${file}settings.py"
        echo "Copied local_${swto}${file}settings.py over local${file}settings.py"
    done
    echo -e "\033[32mAll local files switched to '$swto' project correctly.\033[0m"
else
    if $check; then
        echo -e "\033[31mswproj diff detected in\033[0m $compare1 :"
        echo
        colordiff $compare1 $compare2
        firsttwo
    else
        echo -e "\033[31mNo changes made due to unmet conditions\033[0m"
        echo "Use '<project> --check' to see diffs with another project"
        firsttwo
        exit 1
    fi
fi
