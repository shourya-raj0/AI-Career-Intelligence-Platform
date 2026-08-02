App Flow

Career Intelligence Platform



# 1. Landing Page

### Purpose

Introduce the platform and its value.

### UI Components

Hero section

Features overview

GitHub username input

"Start Analysis" button

### User Action

Enter GitHub username

Click Analyze

### Backend Action

Validate GitHub username

Create analysis session

### Next Screen

→ Analysis Progress

# 2. Analysis Progress

### Purpose

Show real-time progress while building the developer profile.

### UI Components

Progress bar

Current processing step

Estimated remaining time

### Steps Displayed

✓ Fetching repositories   ✓ Analyzing repositories   ✓ Building developer profile   ✓ Fetching jobs   ✓ Matching jobs   ✓ Generating recommendations   ✓ Preparing dashboard





### Next Screen

→ Career Dashboard

# 3. Career Dashboard (Main Screen)

### Purpose

Provide a complete overview of the developer.

### Sections

## Developer Summary

Overall Profile Score

Confidence Score

Experience Level

Top Skills

Preferred Domains

## Skill Overview

Languages

Frameworks

Tools

Databases

Cloud Technologies

## Repository Quality

README Coverage

Testing

CI/CD

Documentation

Project Diversity

## Quick Statistics

Public Repositories

Original Projects

Total Stars

Recent Activity

### User Actions

View Skills

View Jobs

View Recommendations

Export Report

# 4. Job Matches

### Purpose

Display ranked job recommendations.

### Each Job Card contains:

Company

Role

Match Score

Confidence

Location

Employment Type

### Buttons

View Details

Save

Compare

### Clicking "View Details"

Opens Job Details.

# 5. Job Details

## Sections

### Match Breakdown

Displays

Overall Match   88%   Semantic Match   91%   Skill Match   84%   Repository Quality   87%





### Why You Match

Example

Strong Python experience

Multiple AI projects

Good documentation

### Missing Skills

Example

Docker

AWS

CI/CD

### Evidence

Example

Python

Evidence

AI Research Assistant   main.py   Portfolio Website   requirements.txt





### User Actions

View Learning Plan

View Suggested Projects

# 6. Learning Roadmap

### Purpose

Show personalized roadmap.

### Structure

Week 1   Docker   Week 2   AWS Basics   Week 3   Deploy FastAPI   Week 4   CI/CD





### Each section includes

Resource

Estimated Time

Difficulty

# 7. Portfolio Project Suggestions

Instead of saying

Learn Kubernetes

Suggest

Deploy a scalable FastAPI application on Kubernetes.





### Each suggestion contains

Difficulty

Skills Covered

Estimated Duration

Technologies

# 8. Explainability

### Purpose

Build user trust.

### Displays

## Strengths

Strong Backend Development

Good AI Experience

## Weaknesses

Limited Cloud Experience

## Confidence

High

## Evidence

Every recommendation links back to GitHub evidence.

# 9. Export Report

### Options

Markdown (implemented)

PDF (planned / not yet implemented)

### Contents

Developer Summary

Job Matches

Skill Gap

Learning Plan

Suggested Projects

# Error Flow

## Invalid GitHub Username

Show

GitHub profile not found. Please check the username.





## No Public Repositories

Show

Not enough public repositories to analyze.   You can manually enter your skills.   (Phase 2)





## Job API Failure

Show

Unable to fetch live jobs.   Showing cached recommendations.





## Rate Limit

Show

GitHub rate limit exceeded.   Please try again later.





# Complete User Flow

Landing Page       │       ▼ GitHub Username       │       ▼ Validation       │       ▼ Analysis Progress       │       ▼ Career Dashboard       │  ┌────┼──────────────┬──────────────┐  ▼    ▼              ▼              ▼ Jobs  Skills     Recommendations  Export  │  ▼ Job Details  │  ├──────────────┐  ▼              ▼ Learning Plan   Portfolio Projects

