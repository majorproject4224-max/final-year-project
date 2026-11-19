# Community activities

Anyone with a connecT account can organize and join an activity. A student, individual, club or NGO uses the same account flow. An organization name is optional; it is self-described, not verified. Branch and academic year are optional, and no technical skill is required to save an interest-based profile.

## Show with two accounts

1. As the organizer, open Events → Create an activity. Choose Volunteer drive, enter a tree-plantation title, future date, location, city and a participant limit. Select Gardening and Environmental conservation. Leave the organization field blank to show individual organizing.
2. As the participant, open My profile. Select Gardening and Environmental conservation, add the same city, optionally choose My city and online, and save. College details and skills can be left empty.
3. Open Overview. Activities for you shows the drive with explanations based on shared interests and city. No compatibility percentage is displayed.
4. Join from the dashboard or details page. The activity disappears from suggestions and appears under Events → Show → I'm attending.
5. The organizer opens the detail page to see participant names. Other users cannot fetch the participant list. Edit activity changes details without discarding registrations. Leave activity releases the place; deleting an activity removes its embedded registrations.
6. Try a food distribution, photography meetup or coding workshop with different interest tags. Categories describe activities; they do not limit who can join or automatically manufacture matching interests.

## How matching works

This first version uses shared normalized interest tags. Case, surrounding whitespace and duplicates are normalized through the existing normalization function. The forms offer the same suggested interests and accept custom tags. Agriculture and gardening are related concepts, but this version does not silently treat all related words as synonyms: organizers can select both when appropriate.

At least one interest must overlap. Expired, full, own and already joined events are excluded. The optional city preference restricts suggestions to the entered city and online activities. City comparison is textual, not GPS/distance. Users can always browse all upcoming activities independently of their recommendations.

Results consider at most 500 eligible upcoming records and return six, ordered by shared-interest count, same city, then time/ID. This bound suits the prototype; a larger catalog would need measured search/ranking improvements. Empty results explain how to add interests or browse events. Event recommendations work even when the technical-project ML artifacts are unavailable.

## ML scope

The existing K-Means and Random Forest models remain dedicated to technical student/project recommendations. Activity matching does not reuse those model probabilities, retrain them or claim measured volunteer compatibility. A later student–activity classifier needs representative data and defensible labels, for example explicit relevance ratings. A missed click or failure to attend is not automatically an incompatibility label. No paid AI service is added.

## Implementation and limits

- `platform_api/activities.py`: endpoints, capacity rules, participant access and interest suggestions.
- `platform_api/serializers.py`: inclusive profile fields and activity validation.
- MongoDB `events`: existing documents extended with category, interest_tags, city, mode, organization_name and participant_limit. No destructive migration. Existing events remain visible; ones without interest tags are not suggested.
- Capacity checks and joining happen in one atomic document update, including retry deduplication. Reducing capacity also checks attendance atomically. New limits are 1–500; legacy records without a limit have a 500-person ceiling.
- React uses shared activity cards, form and interest suggestions. Times display in the viewer's local time zone.
- No organization verification, waitlists, attendance certificates, activity notifications or new group chat is included. There is no automatic live refresh of participant lists; reload shows new sign-ups.

See API.md for endpoints and TESTING.md for cloud verification.
