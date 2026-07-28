# H6 classifier audit sheet -- part 2 (confirmatory subjects)

**What this is.** A machine read 120 interviewer turns and sorted each one into
one of two boxes. Your job is to sort the same 120 turns yourself, without
seeing what the machine said. Afterwards we compare. If we agree often enough,
the machine's labels get used to build the H6 arms. If we don't, H6 scoring
stops and the instructions the machine was given get rewritten.

**This is the second of two checks.** The first one ran on the 6 development
people and passed. This one runs on the real study subjects, which is the check
that actually gates the science. The bar is the same as last time.

**This sheet is blind on purpose.** The machine's answers are in a separate
file you should not open until you have finished. The rows are shuffled, and
the subject and interview each row came from are deliberately not shown, so
nothing here hints at the answer.

## The two labels

Every row shows three things:

- **PREV** - what the interviewer said last time.
- **GUEST** - what the guest said back.
- **TARGET** - the interviewer's next turn. **This is the only thing you label.**

Write **F** if TARGET is a **follow-up**: it picks up something in GUEST. It
quotes it, questions it, pushes back on it, asks the guest to explain or back
it up, or just asks for more of the same ("Go on.", "Meaning what?").

Write **N** if it's a **new topic**: TARGET brings in material that did not come
from GUEST. A prepared question, a change of subject, a hand-off to the next
segment, a sign-off, or a question aimed at someone else.

## The tricky ones (these are where we're most likely to disagree)

1. **Comment plus question -> judge the question.** "That's alarming. Who
   decides who gets tested?" is **F** - the compliment is filler, the question
   digs into the answer.
2. **Praise then swerve is N.** "Fascinating. Now, the budget vote..." looks
   friendly but takes nothing from GUEST.
3. **Same subject is not enough.** A question can be about the very thing the
   guest just discussed and still be **N** if it takes nothing from what they
   actually said.
4. **Guest dodged, interviewer asks again**: **F** only if TARGET names the
   dodge or quotes the answer. A plain repeat of the original question is **N**.
5. **Going back to the interviewer's own earlier line of questioning**, as if
   the guest's answer hadn't happened, is **N**.
6. **Part from GUEST, part new -> F.**
7. **Judge the words on the page**, not what you think the interviewer meant.

## How to fill this in

Go top to bottom. For each row write `F` or `N` on the **YOUR LABEL** line.
Don't skip and come back - first read, best guess. Every row needs an answer;
if a row is genuinely impossible to judge, write `X` and one word why, and tell
whoever is scoring it (rows marked `X` are dropped, and the check needs at
least 60 answered rows to count).

Text is cut to the same length the machine saw it, so `...` means words were
removed there. That is normal - judge what's shown.

## Coverage

These 120 rows come from **60 different people**, drawn from a pool of
5268 machine labels over 88 study subjects. The plan asks
for at least 60 rows across at least 10 people, so this sheet clears both. None
of these rows appeared on the first sheet, and none of these people were used
in development.

---

### Row 1

```
PREV: They don't have the ground-attack aircraft, like the A-10 Warthogs or the helicopter gun ships or the AC-130 gun ships that would be most effective in a place like Misrata.
GUEST: That's correct, and beyond that, too, they're running out of ammunition. The British, for example, have complained they're running out of precision bombs. Now, that's really very serious, and it suggests to me that there's something much bigger going on than just simply the question of the attacks on Misrata.
TARGET: We're talking with George Joffe of Cambridge University. Whose side is time on in Libya? Stay with us. I'm Neal Conan. It's the TALK OF THE NATION from NPR News.
```

**YOUR LABEL (F or N):** ______

### Row 2

```
PREV: Although besides the grand slam, I mean, for him, just winning the French Open was an achievement because it's taken Djokovic 12 years.
GUEST: Absolutely. There have been demons here in Paris for Novak Djokovic, who, at this point, he's seemingly eclipsed Rafael Nadal, who is a nine-time champion here in Paris, as the most dominant player on clay. And yet, he would come to Paris, he would knock on the door, play some great tennis and get absolutely derailed really unexpectedly. And last year in particular, it looked everything was set up for him. And he ran into Stanislas Wawrinka, who absolutely just played the match of his life to win the final. So now he finally has it. And you can see the relief on his face, you know, three, four, five hours later.
TARGET: Well, as I just said, the last male player to win the gland grand slam was Rod Laver back in 1969. Why has it taken so long for someone to do that again?
```

**YOUR LABEL (F or N):** ______

### Row 3

```
PREV: And the Status of Forces Agreement, known as SOFA, went into effect today, and that among other things mandates the withdrawal of all U.S. troops from Iraq by 2011. Are people talking about that? And how is it affecting them?
GUEST: Well, the SOFA basically states that we will be continuing to work with the Iraqi forces for the remainder of the time that we're here. And it has set a timeline, but our timeline to come home really hasn't changed even according to that. But a lot of the troops now are looking towards the future, knowing that they'll probably wind up going to Afghanistan. So right now, the schedule of deployments, we don't really know how far out that's going to go, and so people are just sort of looking towards getting our job done here and then heading home to their families.
TARGET: And I've also read that most of the changes, at least initially, will take place at the Green Zone, where Iraqis will be in charge as of today.
```

**YOUR LABEL (F or N):** ______

### Row 4

```
PREV: Muhannad Hadi, thank you so much for coming in again, and safe travels to you.
GUEST: Thank you, sir. Thank you.
TARGET: The voice of Muhannad Hadi. He's the World Food Program's emergency coordinator for Syria.
```

**YOUR LABEL (F or N):** ______

### Row 5

```
PREV: But does it surprise you, though, that so many members of your party have fallen in line? I mean, many of them have taken exception to these remarks, but at the end of the day they are supporting him. What does that say?
GUEST: You know, it's this whole thing of party unity. And you don't want to upset party members. And you don't want people to blame you for Hillary Clinton's election. I understand all that. But I think there comes a point where you have to put country first and party second, and this is one of those moments. You know, we need to speak up. And if the party made a mistake, we need to recognize it. We'll be bigger for it. But this could be a huge strategic loss for the Republican Party in the short-term and long-term.
TARGET: But before I let you go, our earlier guest, as I mentioned - Jacob Montilijo Monty, who's an immigration lawyer in Houston - said he also finds Donald Trump's comments repugnant. But he also said that he feels that it's possible that he could be the one figure who, because of his appeal to these groups who are so hostile to immigrants, that perhaps he could be the person who could actually seal the deal on immigration reform because he would be trusted by those folks. Do you find that credible?
```

**YOUR LABEL (F or N):** ______

### Row 6

```
PREV: If, I mean, Russia's really good at this, wouldn't they disguise themselves better? Would Russia really want to put so many visible signs out there in the cybersecurity world that it was them and be identified?
GUEST: ... to discover that, you know, there's not just the DNC, there's, you know, a thousand other people that have been hacked, all of whom are very narrowly tied to Russian military interests - they're hacks of NATO; they're hacks of the German parliament; they're hacks of journalists that are reporting on things that Russia is not, you know, very happy are being reported on - you stop quite quickly to build up this picture where in order for it to be someone else, it really has to be someone that is prolific who is doing this full-time. There's nobody else who would be willing to put that sort of cash, that sort of effort into doing those types of hacks.
TARGET: But you said something very important there. You're saying that Russia, in your words, screwed up here.
```

**YOUR LABEL (F or N):** ______

### Row 7

```
PREV: ... As we've seen in surveys, for example, white Americans tend to have a great deal of confidence in the criminal justice system and in the police as a part of that. African-Americans, the surveys tell us, have far less confidence in the criminal justice system more broadly and police in particular. Is that a problem, and is that overcomeable (ph)?
GUEST: Yes, it's absolutely a problem. Can it be dealt with? I am alternatively optimistic and pessimistic about this. I'm optimistic because I see police agencies across the country doing some really good things, trying to address root causes of distrust. And then I'm pessimistic because this is not new. Policing in this country has gotten significantly better, but it hasn't always gotten better in the right ways. And it still has significantly farther to go. Whether or not it will ever get there, I don't know. I suppose my answer to that question depends on my mood. And in the aftermath of a hung jury, I'm not feeling particularly optimistic today.
TARGET: That's Seth Stoughton. He is a professor of law at the University of South Carolina, where his scholarship focuses on police procedure. He also teaches criminal and criminal procedure. He was kind enough to join us from South Carolina Public Radio, which is in Columbia. Professor Stoughton, thank you so much for speaking with us.
```

**YOUR LABEL (F or N):** ______

### Row 8

```
PREV: Something important. Ed Miller with us from "America`s Most Wanted." Very quickly, to a high-profile criminal profiler that helps us here on the show quite often, Pat Brown. Pat, very quickly. We`ve only got 30 seconds left before break. How do you establish height and weight from a photo?
GUEST: Jennifer, I am going to find you! So you stay, be smart, and I will find you. We will find you. We love you. You know that. And we`ll find you.
TARGET: OK. OK. Good point. Everyone take a look at this. This was taken very soon after Jennifer`s car was found abandoned. Please help us.
```

**YOUR LABEL (F or N):** ______

### Row 9

```
PREV: Now, as we understand it, as we are speaking now, we understand that there has been no credible claim of responsibility for the crash. So two questions I have about that. How do you determine what's a credible claim? And what do we make of the fact that there does not appear to have been one in this case?
GUEST: Well, it is unusual that you don't have a claim of responsibility if this actually was an organized, directed terrorist event. Terrorist organizations like to lay claim to these types of attacks. Recall that ISIS, in bringing down the Metrojet Russian airliner out of Sharm el-Sheikh in the Sinai, was fairly quick in laying claim, and then later provided additional evidence in Dabiq, their online magazine, to show exactly how they brought down the plane. And so for propaganda value, for purposes of disseminating messages and information about the bombs, these groups will tend to be fairly quick in attributing these attacks to their activities.
TARGET: And so they want to give evidence that it's credible?
```

**YOUR LABEL (F or N):** ______

### Row 10

```
PREV: And so how was he killed?
GUEST: He was coming back from an event in Latifiya to his home in Baghdad when they were stopped at a checkpoint by men in military uniform. It was a convoy of about nine people. They were kidnapped and their bodies were found in a Shia district in the north of Baghdad.
TARGET: And his son was with him, right? He was also killed.
```

**YOUR LABEL (F or N):** ______

### Row 11

```
PREV: And where would you suggest a venue?
GUEST: I think that there are multiple venues. There are advocacy groups scattered throughout the United States, and I think speaking to those groups is important - as scientists, bringing information to the conversation. I think that shows like these are another venue. I think as scientists, we haven't even began to explore the wonderful, you know, the wonderful world of Tweeter(ph), of tweeting and things like that. But there are - we're not very good about communicating the information. We do it in dry journal format when sometimes a picture will suffice and be much more effective at communicating an idea.
TARGET: Well, I want to thank you all for taking time to join us, and we'll be watching to see how well you are able to communicate those ideas, especially if Congress hold hearings and has invited you folks to come up there. Maybe you can tell them what - instead of them talking to you, what you think about science.
```

**YOUR LABEL (F or N):** ______

### Row 12

```
PREV: Venezuela is Latin America's biggest exporter of crude oil. In January, the country produced 2.5 million barrels a day. Much of that was coming to the U.S. Is there a concern that the situation there, the unrest could affect the oil industry?
GUEST: Now, in 2002, towards the end of that year, there was a major oil strike, which completely crippled the oil supply at this country. And it lasted about two or three months back then. Now, what happens after that 2002 event was that Chavez and the government sacked half the workforce and replaced them with government supporters. And that's still the case now. So it's very unlikely they'll go on strike, but it's, of course, a possibility and a means to re-cripple this government.
TARGET: That's reporter Girish Gupta who's been covering the protests in Venezuela. Girish, thank you.
```

**YOUR LABEL (F or N):** ______

### Row 13

```
PREV: And let us begin with the men. Novak Djokovic dispatched his old nemesis Rafael Nadal in the quarterfinals and looked to be cruising to his first ever French Open victory, and then what happened?
GUEST: And then he ran into an absolutely red-hot Stan Wawrinka, a player who on any given day can beat any given player. He's just not always a consistent guy, so we don't really write him into these final matches or think that he's going to make a big run. But Stan Wawrinka played one of the best matches he's ever played in his career to upend Novak Djokovic in what felt like a to-be coronation ceremony before the serve, who was looking to complete his career slam here at the French Open.
TARGET: And tell us more about him. I mean, he's not young - 30 years old - for a tennis player, but this is his second major in the last year and a half. What's he done to up his game?
```

**YOUR LABEL (F or N):** ______

### Row 14

```
PREV: So what can we, consumers, do in the face of all this? Is there a way to avoid these high rates?
GUEST: ... business elsewhere if you don't like how your credit card issuer is treating you. Second, maintain very, very strong credit reports and very, very strong credit scores and you find yourself somewhat immune to what's going on in the credit environment right now. And last but certainly not least, be very, very selective about where you use your credit card. Be very conscientious of the fact that you issuer sees where you're shopping and sees the patterns that you're exhibiting. So avoid cash advances and avoid using your credit cards at what are referred to as questionable merchants, places like pawn shops, tire retreading stores, massage parlors, marriage counseling. Things like that are going to set off a red flag.
TARGET: And you don't have to stick with the big guys. You can go with the small banks or the credit unions.
```

**YOUR LABEL (F or N):** ______

### Row 15

```
PREV: ... Kansas City Royals need just one more win to claim their second-ever World Series championship. The Mets are going to try to make sure that does not happen. But beyond the big game, this matchup has a unique place in baseball history. Joining us to talk about all of that is Dave Zirin. He writes for The Nation. Welcome, Dave.
GUEST: Hey, great to be here, Michel.
TARGET: Well, I've previously disclosed my fondness for the Mets, having been born and raised in Brooklyn. So you can imagine this is a little bit of a tough day for me. I know you're going to help me get through it. So...
```

**YOUR LABEL (F or N):** ______

### Row 16

```
PREV: Juan, you've been directly involved in these issues yourself. Now you're watching it from more of a remove. What does all this tell you about the government's strategy for combating these terror-financing networks?
GUEST: ... That was used to great effect, obviously, against al-Qaeda in the earlier days, identifying donors and charities, front companies that were used by al-Qaeda to raise and move money, used effectively against Iran. We're still seeing the effects of that today. But what you have here is a hybrid form of terrorist financing, where these groups have really devised clever ways of raising money locally, as well as relying on a resuscitated international donor network to raise funds. And so what you're starting to see - and these designations reflect that - is an attempt by the Treasury to use some of the old tools in the playbook, but to try to adapt to the realities of this new challenge.
TARGET: Juan Zarate is a senior advisor at the Center for Strategic and International Studies and the author of "Treasury's War: The Unleashing Of A New Era Of Financial Warfare." Juan, thanks very much.
```

**YOUR LABEL (F or N):** ______

### Row 17

```
PREV: Huh. What else were people looking for?
GUEST: ... that people didn't know how to spell it. So one of the things that we see online is the different attempts that are made. So they landed on ombre, O-M-B-R-E, which is the French word for shadow. It's also the name for, I think, a card game or something in English, which is why it's there. And also umber with a U, which is, of course, the color. And so they landed on these different pages kind of searching for the correct word, which reminds me of Aleppo. There's a combining form, lepo-, L-E-P-O, which people landed on because Aleppo is the name of a city, which is also in the dictionary, but people didn't know how to spell it.
TARGET: Ah. So people were just searching for lepo- instead of...
```

**YOUR LABEL (F or N):** ______

### Row 18

```
PREV: Now, back in July, there were millions of Egyptians that really welcomed the ouster of Mohamed Morsi, and you heard a lot of assurances that, well, you know, we will get back to a democracy. What is their reaction now?
GUEST: ... against the government. We've seen opposition to the government's policies spread amongst a small group of people who we've considered sort of anti-government activists over the last three years. And we've seen a lot of non-Islamist activists imprisoned in the last couple of weeks. And so that's new. You do hear a lot of private expressions of concern about the direction of country. The continued struggles of the economy, you know, the fact that for most people things do not seem to be getting better. And you also hear a concern about the idea that we're entering a new military era. People seem to realize that that might represent a real step backwards for the country after all this turmoil.
TARGET: Is there worry also that the Muslim Brotherhood supporters might now be more likely to turn to extremism?
```

**YOUR LABEL (F or N):** ______

### Row 19

```
PREV: ... forces carried out widespread arrests of its members, even as they held protest rallies around the capital. It's a massive downfall for the Muslim Brotherhood since July when the military deposed President Mohamed Morsi, the first democratically elected president and a former member of the Brotherhood. For more, we've got Kareem Fahim of the New York Times with us. Welcome.
GUEST: Thanks for having me.
TARGET: Tell us what led to this move to brand the Brotherhood terrorists?
```

**YOUR LABEL (F or N):** ______

### Row 20

```
PREV: I saw one pair of numbers was about 2 to 1 in the '60s versus the '30s, fair or unfair.
GUEST: Exactly. And we see this across many income categories. There's a big partisan gap on these attitudes, but there's an important other element to this in terms of opportunity. We asked, in the same survey about a month ago, can most people get ahead if they're willing to work hard? And you get about 64 percent saying, yes, they can still. And that number dipped a little bit during the recession, but has come back.
TARGET: You said that there's a big partisan divide here. Are Democrats more likely to say the deck is stacked and Republicans more likely to say it's fair?
```

**YOUR LABEL (F or N):** ______

### Row 21

```
PREV: Re-nominated. Do you think she can get confirmed this time?
GUEST: She could probably - well, I think that the right might vote against her. She is not predictable enough. But you know, she's certainly - she's still very busy. She hears cases on the Court of Appeals and is heavily promoting the idea that state supreme court justices should not be elected.
TARGET: Charles Evans Hughes.
```

**YOUR LABEL (F or N):** ______

### Row 22

```
PREV: So, give me a sense of what you're seeing on the streets. What do these protests look and sound like?
GUEST: Well, we're seeing barricades all over Caracas. We're seeing the burning of trash on the streets, the banging of pots and pans, which is a traditional form of protest here. And this is waking people up quite early in the mornings and going on late into the night. Even late last night, there was teargas from authorities. There were people pelting authorities with stones, with petrol bombs. Now, this isn't seeming to go away. This has been going on for about two weeks now in Caracas, and all over the country for even longer. For three to four weeks in the West, where this began, we're seeing even bigger, somewhat more organic protests.
TARGET: Well, we know this country, Girish, is split between people who support the government socialist policies, and you have more affluent Venezuelans who don't support those socialist policies. I mean, who are the people who are on the streets and leading these protests and sustaining them, as you say?
```

**YOUR LABEL (F or N):** ______

### Row 23

```
PREV: And please tell us about these two candidates.
GUEST: Well, the Republican candidate who's running is Debbie Lesko. She's a longtime state legislator - quite conservative. She is the Arizona coordinator for the American Legislative Exchange Council, so that'll give you sort of a feel for her points of view. Her Democratic opponent, who, by the way, is the first time that Democrats have run an opponent in this district since 2002 - is a woman named Hiral Tipirneni. She is of Indian descent, came here with her parents when she was, oh, I think, under 5 years old, grew up and became an emergency room doctor.
TARGET: And based on what you've seen so far in the campaign, does Ms. Lesko cite President Trump as any kind of inspiration or example? What kind of relationship does Ms. Tipirneni seem to have with the national Democrats?
```

**YOUR LABEL (F or N):** ______

### Row 24

```
PREV: ... same sense of urgency. Had this been a 28-year-old male and a 13-year-old girl, I contend, and if we'd seen the rash of male teachers doing the same thing that we've seen over the course of the last two years as we have with female teachers, I think society would be more up in arms than we see right now.
GUEST: Yeah, you're right, Ed. You're exactly right. Men are viewed as predators because that's typically what we are. So it would be more of a predation thing, and as you indicated, I mean, there have been movies made about, wow, you know, a young boy losing his virginity to the older woman. That's just society and just the way it is. I mean, you would definitely believe that if it was an older male having sex with a younger girl, that he coerced her into doing it, whereas with a boy, it's just, like, well, you know, boys will be boys; you've got to lose it sometime.
TARGET: ...E.R., is suggesting that.
```

**YOUR LABEL (F or N):** ______

### Row 25

```
PREV: Nicholas de Torrente, thank you for stopping by and we wish you and your organization much luck. I guess you have to have a lot of patience at this point. Don't you?
GUEST: Yes. Thank you very much, Paula, for having me.
TARGET: And we will be back in just a moment. I'm sorry I have to cut you off. When we come back, one of our guests here at the table predicted this war was going to be a cakewalk. Has he been vindicated? And is the battle for Iraq really simply the opening shot in a new war? Stay with us.
```

**YOUR LABEL (F or N):** ______

### Row 26

```
PREV: Everybody is denying it.
GUEST: Of course. Well, look, President Zia, when he was the president of Pakistan, for 11 years lied to us about their own nuclear program. They said, No, we're not doing it.
TARGET: All right. Midge Decter, we're going to have to leave it right there. Midge's new book, let me make sure I get the title right, "Rumsfeld, A Personal Portrait." A book about Donald Rumsfeld. Arnaud de Borchgrave, he's the editor-in-chief of United Press International. He's with the Center for Strategic and International Studies here in Washington, D.C. Lawrence Korb, former Pentagon official, now with the Center for American Progress. Briefly, what is the Center for American Progress?
```

**YOUR LABEL (F or N):** ______

### Row 27

```
PREV: So what does this disputed airspace symbolize?
GUEST: Well, there's two parts of this really. One is, is that the Japanese and Chinese are increasingly in contact with each other across the East China Sea. And that's your fisherman, its government agencies doing surveys for seabed resources and, of course, it's the two militaries. China and Japan however don't have an agreement on a maritime boundary. And this ADIZ that China announced on Saturday also puts the air space above the East China Sea in contest.
TARGET: So how seriously are people taking this latest diplomatic disagreement?
```

**YOUR LABEL (F or N):** ______

### Row 28

```
PREV: And Jug, thank you very much.
GUEST: Yes.
TARGET: Why economically damage them for something they didn't do?
```

**YOUR LABEL (F or N):** ______

### Row 29

```
PREV: ... mass in his church early this week seemed to really strike another part of the French identity for a lot of people. The chief imam of Paris' grand mosque even called for reform of Islam in France - didn't go into any details, as I understand it. How would you describe with those turns of events the mood in France?
GUEST: The murder of this priest was really a big shock. But I think the leaders of the churches, of the Catholic Church and some imams have also reacted quite responsibly, telling people, you know, don't give up your values. This is what they want. This is what the terrorists want. If you give way to anger and revenge, they will have won. Don't give up your way of life, and I think people understand this.
TARGET: Sylvie Kauffmann is editorial director of Le Monde newspaper. She spoke to us from Paris. Thank you so much.
```

**YOUR LABEL (F or N):** ______

### Row 30

```
PREV: (Laughter).
GUEST: ...Because it seems like the Russian government's decided to declare them an extremist group because of pamphlets that they distributed. And the formal argument by the Justice Ministry was that those pamphlets incited hatred against other religious groups. Basically they said that, you know, Orthodoxy is not the true way, our way is the true way. And so that's the main sort of part of the government's argument.
TARGET: Now, you mentioned pacifists. That's one of the beliefs the Jehovah's Witnesses are known for - pacifism. They try to be apolitical. People in the United States know them because they knock on doors. They pass out those pamphlets you mentioned. They do seek converts. You may disagree with them. You may dislike them but they don't seem that threatening. How common are Jehovah's Witnesses in Russia?
```

**YOUR LABEL (F or N):** ______

### Row 31

```
PREV: From a distance, Mr. Cordesman, what can you read about the divisions in the military itself? There have, as you noted, been a lot of defections. Some forces still remain loyal to him.
GUEST: ... even some of the most loyal forces to Gadhafi, including the commander of the Libyan special forces, have defected. And we are seeing definitely in the east really serious shifts to support the rebels against Gadhafi. It's far less clear as to what's happening around Tripoli. And there are units scattered into the southwest of Libya where we don't seem to have any reporters or any indication of who their loyalty to is at all. So, we're talking probably out of a force, which on paper is 150,000-170,000, actually being 25,000 at most operational in the field divided between the rebels and Gadhafi in ways which we've really frankly do not understand and seem to be changing by the day.
TARGET: Well, what about calls there have been in the international community to establish some kind of no-fly zone?
```

**YOUR LABEL (F or N):** ______

### Row 32

```
PREV: ... heard from Chuck Todd, the Mark Foley -Congressman Mark Foley - scandal seems to have had some impact. Do voters make any distinction when it comes to the Senate, or what do you get a sense is driving so many voters in the polls, at least, away from, well, even some Republican incumbents who seemed pretty safe earlier this year.
GUEST: You know, I think the Foley scandal per se has not had a direct impact on Senate races. But if you take Mark Foley and continued bad news in Iraq and Bob Woodward's book, State of Denial, which has been quite critical of the administration, and the national security estimates - intelligence estimates - because they were all - all these things happened around the same time. It's almost like it just handed every Republican candidate 20 more pounds of wet sand to carry around.
TARGET: You mean, if you've been standing by the president on Iraq all this time and being a good soldier in the GOP, suddenly it's not such an asset right now.
```

**YOUR LABEL (F or N):** ______

### Row 33

```
PREV: ... the government. There is also an audit that shows that millions and millions of dollars have been wasted by the government, squandered, in terms of preparing the evacuees to get back on their feet. That juxtaposed with this report does not speak well to, as John suggested, being able to deal with catastrophes of this size from the federal government.
GUEST: I do want to give FEMA a slight benefit of a doubt, just a slight benefit, because we do have to remember that at the time that this was going on, unless of course it's still going on right now, there was a huge rush--this was a frenetic rush - to get these people from New Orleans into--from the South rather--into places that are safe. You know, you talked about the $399 rooms in Chicago. A little bit of research into that, that was actually a family of - I mean, it was two families and it included meals, so it wasn't really quite as bad as the numbers seemed, necessarily.
TARGET: Well, but then it's almost like the Defense Department and that $9,000 hammer or whatever it was with the toilet seats, you know. There is a sense of whether that be the case or paying $375 a day for a beachfront condo to put folks in. There was a fiasco of the debit card that was given out. Much of this was response to the idea that a lot of heat was being taken, and rather than somebody taking a step back and a breath and saying, let's get a hold of this, they just started, as we heard from Christopher Shays, admitting that even the Congress just started appropriating money because the heat from the public was white hot ...
```

**YOUR LABEL (F or N):** ______

### Row 34

```
PREV: A former British intelligence officer who was reporting this for opposition research within the Republican Party, but they did not report these salacious details. That was another news organization. That's just...
GUEST: But they highlighted the story.
TARGET: Well, OK. Different points of view on that, but that's where I'm glad we have the range of views.
```

**YOUR LABEL (F or N):** ______

### Row 35

```
PREV: Do you -- what do you hope President Trump says to President Putin then, when he meets him a day or two after the NATO Summit?
GUEST: Well, I hope he'll come from the NATO Summit, where we have sent a clear message of unity and resolve (ph) and that he will make clear that we'll never except the inexaction (ph) of Kramir (ph) -- this is a violation of international law. And that we see what is going on in the Ukraine for example. And that there is a possibility to sit down and solve (ph) these problems if there is the willingness on the other side really to work for peace. So there are many topics to debate, but the most important one is to come from this Summit with the strong message of resolve and unity.
TARGET: And finally, you are a close ally of the Chancellor, you're Deputy Leader of her party -- how is she taking this constant being a target of the rough, the anger, the Tweets of the President of the United States?
```

**YOUR LABEL (F or N):** ______

### Row 36

```
PREV: Rich Jaroslovsky, he joined us from Palo Alto in California. Rich, thank you very much for all these additions to my wish list.
GUEST: Thank you for having me.
TARGET: Rich Jaroslovsky is a columnist for Bloomberg News.
```

**YOUR LABEL (F or N):** ______

### Row 37

```
PREV: Hi, Francis.
GUEST: ... the reason that the market is so jittery and speculators are betting is that, you know, how do we know that, you know, there won't be protests and oil won't be disrupted say, from Iran? And that could be four million barrels a day, because there gets to be a number at which we can't actually replace the oil that's lost in the market. And we had that experience in 1979, and it caused a huge dislocation here in the United States. You all might remember, depending on your age. You know, I remember driving to school with my father, and we would have to get in line because it was an odd - we have an odd-number license plate...
TARGET: That's right. Yeah.
```

**YOUR LABEL (F or N):** ______

### Row 38

```
PREV: This chaos erupted just shortly after, in fact, the United States, among others, recognized the Transitional National Council as the legitimate government of Libya.
GUEST: That's in fact correct. Just a few days afterwards, and Britain and the United States have joined France and Turkey in recognizing the council. There are now some 20 countries that do. And the embarrassment is, of course - and is an embarrassment for NATO as well - that nobody knows whether there's really a workable organization there that could take over the administration of a country united after the civil war.
TARGET: And indeed there is doubt about delivering large supplies of unfrozen Libyan assets to such a fragile regime.
```

**YOUR LABEL (F or N):** ______

### Row 39

```
PREV: So it's my understanding that this is generated in part both internally and externally - that there are employees who felt that this was offensive. What about the Chick-Fil-A on the other side of it when progressives didn't want to eat at Chick-Fil-A? Did you think that was ridiculous, too?
GUEST: Again, Chick-Fil-A is, again, a great organization giving great food. And they are run by Christian values, and that's what is important to them and that's what they follow. But, again, they serve people from all backgrounds and all ethnicities. Kellogg made a very important decision not to serve and not to market on Breitbart's publication.
TARGET: And some are even saying that they're - they are donating in the name of family members who voted for President-elect Donald Trump, and that's the way that they are translating their rage and disappointment. So, Puneet, why don't I start with you on this? What do you think about that?
```

**YOUR LABEL (F or N):** ______

### Row 40

```
PREV: Should the United States be preparing for an era after Musharraf?
GUEST: I think so. I think we should have been preparing for this a long time ago. In fact, if there's a failure, the America policy was not to anticipate this kind of event four or five years ago. I never thought that Musharraf was the kind of man - a strong, effective leader. He's a strong leader with signs of weakness, but he's never been that effective. In fairness, perhaps, he can't do all the things we asked him to do. We've asked him to go after al-Qaida, to round up Taliban, to stop the nuclear program, and now to revive democracy in Pakistan. Perhaps, no Pakistani leader could have done all of those things.
TARGET: Given the amount of money the U.S. has poured into the Pakistani military, does it have much leverage?
```

**YOUR LABEL (F or N):** ______

### Row 41

```
PREV: Michelle Faul is Nigeria bureau chief for the Associated Press. She's been able to interview one of the girls who was able to flee on the night of the first kidnapping. Good morning.
GUEST: Good morning to you, Renee.
TARGET: Tell us her story.
```

**YOUR LABEL (F or N):** ______

### Row 42

```
PREV: That would be a big change from the Obama administration's decision, right?
GUEST: ... and no. The state Obama position was, the time has come for Assad to step aside. The reality was, there was nothing on the ground that was really leading to that. And there had been a lot of folks inside the Obama administration that had worried about the fact that American influence wasn't there and that Russia and Iran were having an increasingly large role. So, in some ways, it's recognizing a reality that was long left not said from the podium. And also, Spicer went on to say, but don't go too far here. Look, it would be hard to imagine that Mattis, General Mattis, secretary of defense, getting much closer without a wholesale change of policy in Syria.
TARGET: Last question, do these talks raise or lower the expectations for the talks in Geneva next month? Do they go higher or do they go lower?
```

**YOUR LABEL (F or N):** ______

### Row 43

```
PREV: If he makes money from the book, which he will, Fred, don't you get a good part of it?
GUEST: Not unless we go for it because you can bet that he is already on the assumption he's been given the money, which I assume, you can bet that he squirreled it away and it has been managed to get to him in some circuitous way with the help, I might add, of course, of Regan Books and of FOX. They have helped him avoid the judgment, which makes for an additional outrageous piece of news in this situation.
TARGET: You know, Fred, these days the talk is always of closure. Could it be -- could there be one good side of this that in admitting this you're at least finding out what actually happened that night?
```

**YOUR LABEL (F or N):** ______

### Row 44

```
PREV: And do they say why?
GUEST: Well, you can certainly infer from strong opposition to President Bush and frustration with the government generally that is driving these numbers up, and the opposition to war in Iraq, obviously.
TARGET: Carroll Doherty of the Pew Research Center for People and the Press. Thank you.
```

**YOUR LABEL (F or N):** ______

### Row 45

```
PREV: ... makes its debut in two weeks. But tonight it's already making headlines. And there's a TV special in the works. Joining me in Phoenix, Arizona is Fred Goldman, the father of Ron Goldman, who was brutally murdered. And, here in Los Angeles, Kim Goldman, Fred's daughter and Ron's sister. What was your first reaction, Fred, when you heard about this?
GUEST: Appalled. I don't know other -- there were a lot of other words but none of them we want to use on TV. It was amazing to me that this whole thing has gotten as far as it's gotten. Nothing would surprise me that this S.O.B. would do but the fact that someone is willing to publish this garbage that FOX is willing to put in on air, is just morally despicable to me.
TARGET: But they are all...
```

**YOUR LABEL (F or N):** ______

### Row 46

```
PREV: Debbie, in a year when there was a solid Democratic sweep, would you have expected broader gains among women? Most of the women who were running were Democrats.
GUEST: Well, what we did see was a story of party here, even in the women's races. While we do have 10 brand-new women who've been elected to the House, eight of those women were Democrats, and we saw no losses among the Democratic incumbent women, but we in fact did lose four Republican women from the House, and there's still some of these undecided races that involve Republican. So there's the potential to lose even more. So it's a good news story for Democratic and a not so good news story for the Republican women.
TARGET: In past years, some elections have been considered, or at least one has been considered the year of the woman. You wouldn't consider that the case this year?
```

**YOUR LABEL (F or N):** ______

### Row 47

```
PREV: And that's an argument that certainly Herman Cain has been making, Andra Gillespie.
GUEST: ... Republican Party or to discount the fact that there have always been black Republicans. But black Republicans tend to favor individual preferences over group preferences, and that tends to explain their voting behavior. So while it's great that Herman Cain as an individual has been able to rise through the ranks of this primary season, that still doesn't negate the fact that blacks perceive the Republican Party as a whole as being weaker in terms of addressing issues of concern to African-Americans as a group. And until there's change on that regard or until the racial climate changes in the United States, we're probably going to see the same type of pattern that we've witnessed for the last 45 years.
TARGET: Well, one of those black Republicans joins us now, Republican Congressman Allen West of Florida, an African-American conservative elected to office in 2010 with support of the Tea Party. And he joins us by phone from Florida. Congressman, thanks very much for joining us today.
```

**YOUR LABEL (F or N):** ______

### Row 48

```
PREV: But is there a religious conversion involved?
GUEST: ... masculinity. It's about being superior to everyone else and finding an outlet for their desire to acquire redemption. Of course at some point then there comes a theological justification. But it's fair to say that many of them are not terribly interested in theology. And that's also why I think this is so attractive to former criminals because ISIS in many ways is the complete perfect fit for this kind of person. In contrast to al-Qaida, ISIS no longer tries to engage in serious theological discourse. It doesn't try to impress people with its theological credentials. It really offers a sort of shortcut to redemption, and therefore it appeals to people whose desire to acquire that education is very limited.
TARGET: You've said more and more that anti-terror work has got to look like traditional police work. So what do you mean by that? How do people address this issue?
```

**YOUR LABEL (F or N):** ______

### Row 49

```
PREV: Well, so their faces will be shown but not - in what other way might they have been shown? When you say...
GUEST: Yes, kind of legal - we will only show a kind of legal pictures, if I may say. But I must say this is something we are still debating. There's a very lively debate in the newsroom. After this editorial, we had a meeting, a kind of spontaneous meeting, and the whole newsroom took part. And we had a very good discussion on this. We, you know, this - we're having a lot of debates in France at the moment about terrorism, so this is just one of them.
TARGET: Well - but also let me be clear. A mug shot is quite a bit different than these ISIS or Islamic State martyr pictures sometimes where these guys often quite glamorous.
```

**YOUR LABEL (F or N):** ______

### Row 50

```
PREV: All right. Thank you very much for taking time to be with us today. Happy Earth Day to you next week.
GUEST: Yes. Thank you. And same to you and all the listeners. Thanks.
TARGET: Have a good weekend. Bill is also...
```

**YOUR LABEL (F or N):** ______

### Row 51

```
PREV: ... say that Afghan President Karzai's interest here is born of desperation. He himself is reported to have said that he doesn't think that NATO and the U.S. will win the war, and that he's looking for allies where he can find them. And if that's Pakistan, a country that he, himself has long had antipathy for, then so be it.
GUEST: A stable Afghanistan would allow Afghanistan and Pakistan to open much more trade, and also to open links with Central Asia. And there is always still the possibility that once India and Pakistan reach some kind of an entente on their border, that there would be links with India which would allow Afghanistan and Pakistan to benefit from that transit trade and the fees associated with it.
TARGET: Although that sounds logical what you're saying, but Pakistan's rivalry with India, might that not prevent it from allowing what seems like a positive all-around from actually happening?
```

**YOUR LABEL (F or N):** ______

### Row 52

```
PREV: And so how would you see that playing out, Dov Zakheim?
GUEST: There is - as a matter of fact internal to the defense budget there is a problem that mirrors the growth of entitlements in the federal budget writ large. We have the same problem internal to the defense budget.
TARGET: All right. Well, Kyle, thanks for your service and thanks for your phone call.
```

**YOUR LABEL (F or N):** ______

### Row 53

```
PREV: ... its Twitter account to report what words people have been searching for most and to clear up any misconceptions. I learned, for instance, that unproud is in fact a word. Peter Sokolowski is a lexicographer at Merriam-Webster, and he joins us now from our member station WFCR to tell us how the 2016 election is affecting our vocabulary. Hi, Peter.
GUEST: How are you?
TARGET: I am doing well. So many words. So many words.
```

**YOUR LABEL (F or N):** ______

### Row 54

```
PREV: I get why Russia is pushing for these talks, why they're arranged these talks, but what is Turkey's deal in all this? Russia is support Assad. Turkey is sponsoring these opposition groups, these rebel groups. Now on the same page, pushing for talks now. Why?
GUEST: Russia's hand has been strengthened by the fact that they have been all in versus the U.S., and many others who have been dipping their toe in the water for years. Right now, what you see is Turkey seeing something to be gained by being closer to Russia. It's not sure how it feels about the Americans. And it certainly is not happy about the fact that Syrian Kurds are part of the American alliance. So, I think it's just about your best interest and what makes the most sense if you are Turkey right now, for them.
TARGET: Well, the goal here is pretty limited, potentially to extend the ceasefire. There's no talk of a wider political settlement, which I think they'll do next month in Geneva. Is there a feeling that Russia is essentially trying to sideline those Geneva talks and move the entire political process into its own sphere?
```

**YOUR LABEL (F or N):** ______

### Row 55

```
PREV: Right.
GUEST: Yeah. It does seem like a little bit of a twist, doesn't it? But the Trump administration says that this is something that has to be controlled by the federal government. And once again, it's not the only time that the Justice Department has gone after California for taking it one step too far from policies that the Trump administration has enacted. That's why you've seen cases on things like immigration and carbon emissions and so forth.
TARGET: So what does this mean? I mean, in the interim, does the state law hold? Can it keep doing what it wants to? And what are the national implications for this suit?
```

**YOUR LABEL (F or N):** ______

### Row 56

```
PREV: To talk about that, we're joined once again by John Ulzheimer. He's a credit expert with Credit.com. Welcome back to the program.
GUEST: Thank you so much for having me back.
TARGET: Now, it was supposed to be harder for credit card companies to raise rates. But since February, when the Card Act took effect, some credit card customers are finding that they're actually paying higher rates. Why is this happening?
```

**YOUR LABEL (F or N):** ______

### Row 57

```
PREV: Who's shooting at you?
GUEST: It's not important, really, who's shooting at us. We honestly don't know. I mean, for us it doesn't make any difference who is shooting at us. I personally don't believe we are a direct target, but those are the calculated risks that I'm talking about. You know, when you're going somewhere, and you see a lot of military activities happening, then you decide - do I go there today, or do I come back tomorrow?
TARGET: The situation that you've described - how does this conflict compare to other conflict zones that you've worked in, in your career?
```

**YOUR LABEL (F or N):** ______

### Row 58

```
PREV: That's what I wondered. I wondered if voters there might be feeling a bit of scandal fatigue. The former governor, Jim McGreevy, is out right now hawking his book.
GUEST: That's right. There was a state senator who pleaded guilty a couple of weeks ago to corruption. There are rumors of more indictments. Even in New Jersey, they might hit scandal fatigue. But I have to tell you, New Jersey's very blue state and Republicans have struggled there in good political environments for them. This is not a good environment. But looking at the data, you know, consistently over the last three or four months, Tom Kean is more than holding his own here.
TARGET: MS. DUFFY: Thank you.
```

**YOUR LABEL (F or N):** ______

### Row 59

```
PREV: So a few extreme comments, they're painting the whole...
GUEST: It helps them all. They all can jump on it. The Pennsylvania candidate started using it in his race, quoting the Delaware candidate, you know. And it's an easy thing to throw in when you're down in the numbers.
TARGET: And that's a term that no one will use in their campaign ad.
```

**YOUR LABEL (F or N):** ______

### Row 60

```
PREV: So next week, Vice President Joe Biden is scheduled to visit the region. He's going to China, Japan and South Korea. What are you going to be watching for out of that trip?
GUEST: Well, clearly there'll be two pieces of the puzzle for the vice president. The first, of course, will be to reassure allies - first and foremost Japan but also South Korea. This Chinese announcement has not only affected Japan's air defenses but also affects South Korea. On the second side of Vice President Biden's trip will be his conversation with Beijing. And I expect that that conversation will focus very clearly on what this air defense ambition of the Chinese is really all about.
TARGET: That's Sheila Smith. She's senior fellow for Japan Studies with the Council on Foreign Relations. Thank you.
```

**YOUR LABEL (F or N):** ______

### Row 61

```
PREV: And is there perceptible increase in the number of skiers who are killed in avalanches?
GUEST: ... experience, are expert skiers who have taken avalanche training. There was this case of a woman, Olivia Buchanan, who died on Tuesday around Silverton, Colorado. And she had, you know, avalanche level-two training, was actually studying snow science at Montana State University. So snow safety experts are now focusing more than ever on what are called human factors rather than trying to, you know, teach people how to analyze the snow to say whether the snow stability is good. So these are questions like, you know, are you being lured into a trap by groupthink? Do you want to impress your friends? And more often than not in an avalanche fatality, several of these factors are going to be present.
TARGET: Are experienced skiers just pushing themselves more?
```

**YOUR LABEL (F or N):** ______

### Row 62

```
PREV: What is the reward, now, Beth?
GUEST: Well, now, it's $1 million for her safe return, then, $100,000 for her whereabouts.
TARGET: Do you chalk it up to the limited experience of Aruban police?
```

**YOUR LABEL (F or N):** ______

### Row 63

```
PREV: So Windows 8, little bit of a catch-up. How innovative is it, though?
GUEST: Well, it is innovative. But what Microsoft is doing - it's sort of a Hail Mary pass, in that what they're trying to do is create a completely new interface for Windows that is more at home in a world of tablets and touch screens; while at the same time, trying to not shock Windows users, and to maintain compatibility with the huge universe of software that's already been written for previous versions of Windows.
TARGET: So let me get this straight: This new user interface, on the new Windows 8, is a - kind of combination of things?
```

**YOUR LABEL (F or N):** ______

### Row 64

```
PREV: Ted Shaw, thank you so much for coming on. We appreciate it.
GUEST: Thank you.
TARGET: Again, that was Democratic presidential candidate John Edwards. To hear our complete interview, tune in tomorrow.
```

**YOUR LABEL (F or N):** ______

### Row 65

```
PREV: Didn't rule it out. And Craig Gilbert, is that enough of an indication that he might be interested in ruling it in?
GUEST: Well, it's hard to imagine it being worse terrain than it was in 2010. It was the best Republican year since 1938 in Wisconsin. But - and it's a presidential electorate. It's going to be a huge electorate. There'll be massive turnout. But you're right. I mean, Wisconsin was won, I think, by 14 points by Barack Obama, but its history is that of much more of a 50-50 state. It was 50-50 in 2000 and 2004.
TARGET: Mike, thanks very much for the phone call. Might we get some better idea of the shape of the political terrain come July 12?
```

**YOUR LABEL (F or N):** ______

### Row 66

```
PREV: You mentioned UNIFIL. UNIFIL is the United Nations force that's been in southern Lebanon for decades now.
GUEST: That's right. And time after time, it has simply had to sit by and been unable to act. It has taken casualties recently, but it's never had the strength to really challenge anyone.
TARGET: Secretary of State Condoleezza Rice was asked about this international peacekeeping force today and was specifically asked whether the U.S. would be willing to contribute boots on the ground, troops on the ground, and she said, I do not think it is anticipated that U.S. ground forces are expected for that force.
```

**YOUR LABEL (F or N):** ______

### Row 67

```
PREV: Tony, thanks so much. We appreciate it.
GUEST: Thanks for having me.
TARGET: I guess that's the only way they can respond. It is amazing to me to think back, though. It was 2002 when The Boston Globe broke the story about the sex abuse crisis in the beginning within the American church. And we are here 16 years later, and these revelations are still coming out.
```

**YOUR LABEL (F or N):** ______

### Row 68

```
PREV: Bob, it just seems to me, though, and I'm going to go back to my first point, which I don't know that we spoke to...
GUEST: Yeah.
TARGET: That being said, Bob, again, I go back to the idea that society seemingly does not see this with the same sense of urgency. Had this been a 28-year-old male and a 13-year-old girl, I contend, and if we'd seen the rash of male teachers doing the same thing that we've seen over the course of the last two years as we have with female teachers, I think society would be more up in arms than we see right now.
```

**YOUR LABEL (F or N):** ______

### Row 69

```
PREV: It's just so tempting to look at this is as something that, you know, could possibly spell the death knell of cable. And you just - you really don't think that's it.
GUEST: ... water of seeing what happens should the cable bundle disappear, but I believe that the cable bundle is strong. I believe that ESPN wouldn't do anything to hurt the cable bundle since that's where they make most of their money. So I think that this is a very early test to see how many broadband-only homes would subscribe to this sort of service. I think that it's an early test to see what the sort of price points are that people would pay for sports or pay for channels like ESPN - maybe a first a la carte test of sorts. But I don't think that this is - this means that the cable bundle's going to collapse anytime soon.
TARGET: John Ourand is a media reporter with the Sports Business Journal. Thank you very much.
```

**YOUR LABEL (F or N):** ______

### Row 70

```
PREV: Welcome, Mary Kate.
GUEST: Thanks for having me.
TARGET: Mary Kate Cary, before the word came out about Priebus leaving, he was in the news for some comments made by his colleague, the new communications director, Anthony Scaramucci. Mr. Scaramucci gave a very colorful interview to The New Yorker. He took shots at Priebus. He took shots at Chief Strategist Steve Bannon. I mean, you're a communications professional. What did you think when you saw all this?
```

**YOUR LABEL (F or N):** ______

### Row 71

```
PREV: Take Barry Bonds, for example. Some say racism is there because of baseball's reluctance to embrace him, but it seems more complicated than that. What does it say about race relations to you, in about a minute or so?
GUEST: Well, one of the things that says that on sports radio, you get some of the most honest discussions in this country about race and racism - as frightening as that sounds. Because people call in, they defend Barry Bonds. People call in and say they hate Barry Bonds. One side says it's racist. The other side says it's not racist. And in the middle of that, you get a view, a sneak - a little view, about how divided, I think, in many respects, we still are in this country on the issue of race or racism. And in a weird, ironic twist, it's presented in the form of Barry Bonds.
TARGET: Yet, with all of that, all the things that we have discussed so far and even the scary title of your book about the terrordome, you do have hope, right?
```

**YOUR LABEL (F or N):** ______

### Row 72

```
PREV: So let's talk about esports, the business of esports. It's been described as the next big thing. How big is the sport right now? How big do you think it could get?
GUEST: The sport right now is not very big, but the potential is huge. And one of the reasons there's such a big potential is that the typical esports viewer and esports player are young males. Those are people that don't watch television. They've never watched television. We talk about cord-cutters in the business. These are cord-nevers. And so advertisers are desperate to try to reach them because they can't reach them anywhere else. So you have companies like Turner Sports, the Big Agency, WME-IMG - they see that advertisers want to reach this group, so they're all trying to get into that group to sort of prove that advertisers should go with them in order to build up the business.
TARGET: Where is the money coming from, though? And sort of where is it going? Where are they investing the money in?
```

**YOUR LABEL (F or N):** ______

### Row 73

```
PREV: But if the Egyptians said to the PLO and the Palestinian Authority, are you prepared to come back to Gaza and to make security guarantees there so that you will make sure that Hamas does not rearm? Is the PLO prepared to do that? Does it have the capacity to do that at this stage?
GUEST: Well, the interesting aspect of all these ongoing efforts is that President Abbas today acts as the president of the Palestinian National Authority which is formed with the approval of all the political factions. That gives him a moral mandate to speak on behalf of all the Palestinian people and I believe that any future agreement to end this conflict that is going on in Gaza today will involve the Palestinian Authority in whatever arrangement that will be made in the Gaza Strip.
TARGET: But even though he's the head of that government, President Abbas didn't order the rocket barrages out of Gaza against Israel and he doesn't seem to be in the position to stop them.
```

**YOUR LABEL (F or N):** ______

### Row 74

```
PREV: The beneficiaries included Iran's U.S.-backed king, Shah Reza Pahlavi. To be sure, many countries received what Iran did - their own small reactors, their own dollops of fuel.
GUEST: It was only in Iran, as a result of the oil boom of the 1970s, that the nuclear program morphed into a full-fledged civilian nuclear program.
TARGET: Oh, because the Iranians had the money to exploit the knowledge they were given?
```

**YOUR LABEL (F or N):** ______

### Row 75

```
PREV: Were there some communities in Alaska that were counting on this project?
GUEST: I would say the state was highly counting on this project. When you look at the Alaska's state budget and the challenges that are facing the state in the coming years, this is a crisis for Alaska. They have declining production, lower oil prices and higher, higher social costs. I think it's difficult for Shell, but it's even more difficult for the state of Alaska.
TARGET: Amy Myers Jaffe is a professor of energy and sustainability at the University of California, Davis. Professor, thanks so much.
```

**YOUR LABEL (F or N):** ______

### Row 76

```
PREV: And what's her background?
GUEST: Her background - she is a judge of the U.S. Court of Appeals for the Third Circuit, which is the Court of Appeals that gave us Samuel A. Alito. And she's also the wife of the governor of Pennsylvania.
TARGET: Now, let's go next to Sammy, Sammy with us from San Francisco. Sammy, are you there?
```

**YOUR LABEL (F or N):** ______

### Row 77

```
PREV: And now, my producer tells me that you are - when you return, you're looking into going into possibly journalism. Is that true?
GUEST: ... from this experience and interview a lot of my fellow soldiers and officers and found that I really enjoy collecting those interviews and collecting everyone's thoughts for pieces and putting them down into writing, and so I'd love to be able to continue that. And I think it's a really interesting time in journalism. It's a tough time right now because we're sort of moving from the idea of print journalism and subscriptions into a lot of online readership. But from what I've read, readership online and viewership online is really skyrocketing. So now, you can get those stories out to a much larger audience, which I think will be a great and beneficial aspect in the next couple decades.
TARGET: Yeah. Is there any area you want to focus on when you get back? Any particular subject matter?
```

**YOUR LABEL (F or N):** ______

### Row 78

```
PREV: And I wanted to ask Adam Pertman about some of the bad experiences she had. Yes, of course she had a good experience, too. We can never forget that. But there are people who are looking to profit from this, and there are inducements for some that might be swaying some women to give up their children.
GUEST: Right, so it's the good, the bad and the ugly. The Internet is changing every realm. The difference between all the others, or most of the others, you know, whether it's commerce on the Internet, book selling, collecting taxes, pornography, gambling, whatever it is, there are people looking at it. There are people saying here's the good, here's the bad, how do we regulate it, what's the illegal activity, how do we help people get the most out of this without taking big risks. We haven't done that for adoption, and it affects tens of millions of people.
TARGET: And Adam Pertman, in that process, as we've heard, people are allowed to be, if they wish to be, much more selective, correct?
```

**YOUR LABEL (F or N):** ______

### Row 79

```
PREV: As a police officer, what do you think you are mainly trained to do?
GUEST: We know that the single largest block of training relates to use of force - an average of just over 120 hours. You can compare that to an average of eight hours of de-escalation and conflict avoidance training in police academies. Officer safety or officer survival training often starts on the first day of the police academy where police cadets see very gripping and horrifying videos of other officers being severely beaten or killed. The lessons that start that early on in the police academy really revolve around one basic principle - policing is dangerous, and if you get complacent, you will die.
TARGET: Has the emphasis in training, in your view, changed in recent years?
```

**YOUR LABEL (F or N):** ______

### Row 80

```
PREV: What kind of a role does Benazir Bhutto have to play at this particular point?
GUEST: Well, she would like to share power. She knows that she's not going to be given power and even in an election, which would probably be manipulated, she won't come out as the Pakistan's number one leader. And I believe that she would like to broaden the political community so that other politicians can enter it. The problem is that she and the other leading politicians have deep enmity with each other. So there's this intense jealousy and rivalry among the politicians, which makes it easy for the military to rule.
TARGET: Should the United States be preparing for an era after Musharraf?
```

**YOUR LABEL (F or N):** ______

### Row 81

```
PREV: All right. Following the most powerful Atlantic ocean storm ever recorded Hurricane Irma, talking there to the AP's Donica Coto on Skype from San Juan. Thanks a lot.
GUEST: Thank you very much.
TARGET: NPR's Ruth Sherlock bringing us up to date on the fight against ISIS in Syria. Ruth, thanks a lot. We appreciate it.
```

**YOUR LABEL (F or N):** ______

### Row 82

```
PREV: Do you think anybody will get to Osama bin Laden?
GUEST: I'm convinced that one, he is alive; and, two, that we will eventually get him. A story I filed from there says that he's in Peshawar now, the capital of the North West Frontier province. That information came from a very important tribal leader that I've known for a long time, because I've been in and out of the area for the last 35 years. And he says that he's been -- Osama bin Laden has been inside Peshawar, a city of 3.5 million, since December 9.
TARGET: Why December 9? What was pivotal about that day?
```

**YOUR LABEL (F or N):** ______

### Row 83

```
PREV: Hurricane Irma did not deliver a direct hit to Puerto Rico. And still, more than half the island lost power. Many people still don't have power. Given how fragile the infrastructure is, how long-lasting might the devastation from a storm like Maria turn out to be?
GUEST: Well, it's a huge concern. I mean there's still nearly 70,000 people without power. So they've been without power for two weeks. And now Maria's bearing down. And the governor has not given an exact timeline. But he said, quote, unquote, "it will be a long time" before power's restored. And he said that the infrastructure is just too old and poorly maintained to be able to withstand a hurricane of this size.
TARGET: And a double whammy sounds like it would be very, very difficult to rebound from.
```

**YOUR LABEL (F or N):** ______

### Row 84

```
PREV: At the same time, would people consider ending the business, doing away with Sherpa involvement in commercial expeditions?
GUEST: ... nobody - least of all, the Sherpas - want to end this work. These are really good jobs for these guys, and they've elevated the Sherpas to a near-celebrity status, as an ethnicity. But I think a lot of people are trying to work in different ways, to try and make it safer. But the reality is that the mountain is the mountain. And even if you get fitter, you can get better gear, you can get better science, you can't change the fact that there are avalanches that come down this mountain every single day. And if you put a critical mass of people on this mountain, there's a sense of inevitability that comes with these kinds of tragedies.
TARGET: That's Grayson Schaffer. He's senior editor and writer for Outside Magazine. Thanks so much for talking with us.
```

**YOUR LABEL (F or N):** ______

### Row 85

```
PREV: So that's the way that law works. Thanks very much for coming in.
GUEST: It's a pleasure.
TARGET: And the Republicans only need to pick up four seats. Overall, the Democrats are defending, what, 23 seats.
```

**YOUR LABEL (F or N):** ______

### Row 86

```
PREV: Hi, Emira.
GUEST: Hi, Farai. It's good to be with you.
TARGET: Yes, absolutely. Now let's go to AFRICOM. It's this new U.S. Defense Department African Command. Africa had been split between European command, central command, Pacific command, now it's under a single command unit. Some African nations and some Western watchdog groups are saying this is not a good idea. But the person who was appointed, General William Ward, of course, says this is going to improve security in Africa.
```

**YOUR LABEL (F or N):** ______

### Row 87

```
PREV: And I wanted to ask Adam Pertman about some of the bad experiences she had. Yes, of course she had a good experience, too. We can never forget that. But there are people who are looking to profit from this, and there are inducements for some that might be swaying some women to give up their children.
GUEST: Right, so it's the good, the bad and the ugly. The Internet is changing every realm. The difference between all the others, or most of the others, you know, whether it's commerce on the Internet, book selling, collecting taxes, pornography, gambling, whatever it is, there are people looking at it. There are people saying here's the good, here's the bad, how do we regulate it, what's the illegal activity, how do we help people get the most out of this without taking big risks. We haven't done that for adoption, and it affects tens of millions of people.
TARGET: This is TALK OF THE NATION from NPR News. I'm Neal Conan. We already know that the Internet has dramatically changed the way we communicate, the way we get our music and movies and shop. That same technology has also transformed the process of adoption. Would-be parents and birth mothers often have more options, though online agencies remain largely unregulated, and the shift to the Web offers more possibilities for fraud and other issues.
```

**YOUR LABEL (F or N):** ______

### Row 88

```
PREV: Take the rest of the world as part of our conversation. There are quite a few female leaders internationally. But what has kept America back?
GUEST: ... we have a different system than a lot of the countries that have elected women -parliamentary systems versus our system where the president is elected directly by the voters. And I think that makes - that changes it. And I think a lot of these other countries also have quotas when they run slates as candidates in these parliamentary systems. There are a certain number of women that are required to be on the ballot. And as we all know in this country, if you say the Q word, people run fleeing. And so, I think that if the party has made a real commitment to electing women to office, I think we would have more women in elected office.
TARGET: Here's another point. We've talked about external obstacles and male dominance in the political arena. How do you address the issue of self-perception of women and those self-perceptions that you think perhaps women need to overcome for themselves to increase their visibility in the political arena?
```

**YOUR LABEL (F or N):** ______

### Row 89

```
PREV: And that city was where Musharraf was taken to court today, to face the murder indictment. His lawyer says Musharraf denies all the charges and claims the evidence is fabricated. Well, joining me to talk about this case is Shuja Nawaz. He directs the South Asia Center at the Atlantic Council here in Washington. Welcome. Thanks for coming in.
GUEST: Thank you for having me.
TARGET: First of all, what is the evidence, as far as we know, that Pervez Musharraf was behind the assassination of Benazir Bhutto?
```

**YOUR LABEL (F or N):** ______

### Row 90

```
PREV: So Landrieu's loss really marks the end of an era for Democrats in the Deep South. Can you give us the historical context there?
GUEST: So Democrats had largely controlled the South, so if we go back as far as Reconstruction, Democrats had really dominated the South. And so we can look at classic political science work that talks about the South is a one-party Democratic region. And now we've just seen a shift from it being a one-party Democratic region to it being a one-party Republican region.
TARGET: So Dem. Mary Landrieu had bucked the political trend against Democrats in the South for 18 years. What kept her from extending her streak this year?
```

**YOUR LABEL (F or N):** ______

### Row 91

```
PREV: OK.
GUEST: Also, it was off the track of going to work.
TARGET: Now, why are you talking like that?
```

**YOUR LABEL (F or N):** ______

### Row 92

```
PREV: Oh, part of his vamping up a National Enquirer story...
GUEST: Right.
TARGET: Jim Hobart, in a few seconds, if you're a Republican, does tribalism really take over at this point? Trump is your nominee. You're going to vote for him. You're going to try to save the Senate. If you love Trump, that's great. If you hate Trump, you're still going to do that because you think he's better than Hillary Clinton.
```

**YOUR LABEL (F or N):** ______

### Row 93

```
PREV: Arizona's a border state, although this district would be well north of that. What kind of issue is immigration in the district?
GUEST: Immigration is a huge issue. Immigration is a huge issue all over the state, but certainly in this district as well. This is a district that would go along with Trump's philosophy of, let's build that wall. Let's build it higher, bigger, deeper, you know, whatever, and then we'll deal with the issue of the people who are here later on.
TARGET: So the factors that led to an upset in Pennsylvania, are they at all at play in this district in Arizona?
```

**YOUR LABEL (F or N):** ______

### Row 94

```
PREV: We've seen the reports that, you know, more than 80,000 people fled Fallujah. I mean, it is a very hot time in Iraq right now. I mean, a couple days ago you tweeted, in 4 1/2 years of covering Syria and Iraq, I've never seen conditions this bad. No tents, no water, no words. Are people still living like this?
GUEST: ... to be out of Fallujah. There were others that were saying, you know, this is much worse. We wish we never left. There was one family I was talking to that really stuck out. It was a woman and her children. They'd been sleeping out for three or four days in the desert. They had a disabled son, and he wasn't able to get medication and had chronic pain. His legs were cramping, and he was actually just - the whole time I was speaking to the family he was just screaming in pain. And they had absolutely nothing. They were sitting there with no tent, one blanket between them. And it was really, really harrowing to speak to them.
TARGET: It sounds like attention now, of course, will turn to getting people back home. And also now the next battle, which is for the northern Iraqi city of Mosul. I guess the question is, you know, with ISIS on its heels, as you said, and losing territory in Iraq, are they going to be doubling down in Mosul? I mean, will that make it a much harder fight?
```

**YOUR LABEL (F or N):** ______

### Row 95

```
PREV: I'm just imagining somebody sitting in their car in traffic in Los Angeles listening to this conversation, wondering if they should be watching the skies for a missile coming over from North Korea.
GUEST: I hope that never happens.
TARGET: Well, everybody hopes it never happens. But you're the expert. Should they fear it happening?
```

**YOUR LABEL (F or N):** ______

### Row 96

```
PREV: So suicide and mental health are real issues for our time. And Orlando told our Hari Sreenivasan why despite the perilous locations of his previous films, this was his most challenging yet.
GUEST: Thank you.
TARGET: It's really important conversation on grief. And if you or anyone you know needs help, please contact your national suicide prevention hotline. That is it for now. Thanks for watching and goodbye from New York. END
```

**YOUR LABEL (F or N):** ______

### Row 97

```
PREV: The stock market has long been a leading indicator, has it factored in a Bush victory?
GUEST: ... would have thought that they may have gotten a little bit nervous. You know, we like gridlock, we like do no harm. We like things to be muddled in Washington. It works well, it worked well from -- if you look at from '94, you know, when the Democrats lost the House and, you know, they had the Senate, we had a nice rally. I think, though, this time the Street feels that the victory will be so marginal that if the Republicans take a sweep, they won't be able to do too much too fast, and I think that is why the market has been pretty OK with the way it looks like it is going to turn out.
TARGET: Frank La Salla, BNY Clearing International, great to have you with us this morning.
```

**YOUR LABEL (F or N):** ______

### Row 98

```
PREV: Now, this focus by President Trump isn't new, but it also comes as U.S. Secretary of State Mike Pompeo delivered a Sunday speech basically blasting the Iranian regime. What's the first thing that goes through your mind as you watch all this unfold?
GUEST: The question of what happens next 'cause I don't think we know, and I don't think the president knows. And I'm not sure he's gamed out, you know, starting with pulling out of the Iran deal in the first place or the escalating rhetoric, what is supposed to happen and where it leads. And I think it's fair to be very worried about where it leads.
TARGET: Some people have raised the question of North Korea, looking to a template there from the Trump administration. You know how the Iranians operate. Is that parallel, appropriate?
```

**YOUR LABEL (F or N):** ______

### Row 99

```
PREV: What will all this mean as states begin their once in a decade process of remapping those congressional districts?
GUEST: Next year's the redistricting year. The Census Bureau will deliver the data to the states sometime in early February and March, depending on the state. And then they start drawing lines and it can be a very political process.
TARGET: So, how is it that we wind up with some of these strange districts? The one I described looked like this sort of growing puddle of spilled milk, or almost like a spider reaching out in several directions all at once.
```

**YOUR LABEL (F or N):** ______

### Row 100

```
PREV: You believe the Russians aren't doing enough here to aid this situation. What is it they should be doing? Do you want some sort of military action launched to rescue him? Where are they falling down?
GUEST: They have clear obligations and responsibilities, as you say. They have the responsibility for the safety of aid workers on their territory. And Dagestan is clearly on their territory. And they have responsibilities to ensure his release. What we know is that they're able to communicate -- have been able to communicate with the captors in the past. They've obtained proof of life from him, video, and photos from the captors. We know that they could do a lot more. And really they can and must do more.
TARGET: What is it you would like to see them do?
```

**YOUR LABEL (F or N):** ______

### Row 101

```
PREV: So we want to spend some time on the legacy of Justice Rehnquist, but first, let's ask the big question: Why has Judge Roberts, who until today was just a nominee for an associate justice, been so swiftly moved to the front of the line for chief justice?
GUEST: ... Rehnquist, then Justice Stevens would be the acting chief justice. I don't think that's something they want, and they don't want the vacancy, period. In terms of Justice Roberts' re-nomination for chief justice, it's not really a surprise. I think that there were three options. One was to elevate one of the current sitting associate justices. The other was to nominate somebody fresh to be chief. But John Roberts is a known quantity, he's been vetted, and they have a lot of confidence in his intellectual ability, and he's going to be on the court for 30 years, if he's confirmed, as chief now. So for them, it's a move that I think has a lot of logic to it.
TARGET: Charles, let me just ask you--I don't want to go too deep into talking about Judge Roberts before we get to Rehnquist, but you say that he, as a chief justice, will swing the court further right. What makes you believe that?
```

**YOUR LABEL (F or N):** ______

### Row 102

```
PREV: Are there any leads? Are officials talking about any leads that they have in this investigation so far?
GUEST: You know, officially, officials haven't discussed discussing any leads. Because past attacks of this nature in Russia have often been tied to the insurgency in the Caucasus and Chechnya, I would assume that one of the main sort of suspicions would be that it's an attack by insurgents from that region, but there hasn't been any sort of conclusion of that. Russia's also involved in the conflicts in Syria, and that's also considered a possible motive behind the attack. But in terms of an actual suspect or a person that investigators say that they're looking for, we haven't seen anything in particular yet.
TARGET: I guess it's important to know. How common are attacks like this in Russia?
```

**YOUR LABEL (F or N):** ______

### Row 103

```
PREV: When Karzai departs, what is he going to leave behind that will sustain the very things he cared about which is bringing peace to Afghanistan? He was quite a supporter of women's rights. But what is going to be left after him that will ensure that these goals and efforts will continue?
GUEST: ... for not building neutral, impartial electoral institutions over the past 10 years. So even before we speak about after Karzai, right now there are large questions raised about his intentions of really transferring power the way it should have happened. My criticism is not that he didn't build institutions. The institutions were built in the space that was created over the past 10 years. Even if the president wasn't directing all of his efforts to buildings these institutions, the institutions were built through the international money, through other efforts. But the problem is that the institutions that Karzai leaves behind are fragile, and they could have been much stronger if the president had focused on the mandate that he had.
TARGET: Mujib Mashal is a journalist. His piece in The Atlantic is called, "After Karzai." He joined us from our bureau in Kabul. Thank you very much for joining us.
```

**YOUR LABEL (F or N):** ______

### Row 104

```
PREV: ... amount to the two percent of GDP on your military spending. So the president will continue to criticize you for that. I guess my question is, what do you make of Senator Ambassador Kay Bailey Hutchison's description of President Trump's loud complaint as a strategy to get you all together and to make NATO stronger by having it's militaries stronger?
GUEST: ... defense budget on your defense budget nationally without contributing anything to NATO for example. Therefore I think, and we agreed on that in the alliance. It's worse to look at two other metrics, but our capabilities given to NATO and contributions to NATO missions. And I think (inaudible) is that Germany is the second largest troop contributor to NATO mission overall. We're just - we're just talking about the NATO command structure. Germany is leading the joined support in enabling command the new (inaudible). In order, we are the second largest net payer to NATO. So these are numbers that show that NATO is benefiting from the German contribution, as we all try to contribute as good as possible to
TARGET: OK, so let me take the first bit first. President Trump saying I don't know what we the United States get out of essentially protecting you Germany, you Europe. Could you answer that first, what's in it for the U.S.?
```

**YOUR LABEL (F or N):** ______

### Row 105

```
PREV: When you look at technology -- we were flipping through the paper earlier: There's a full-page ad by one of the box makers, you know, essentially selling you a computer and a free printer for $699...
GUEST: Right.
TARGET: ... as you look at the box makers and the tech group as a whole, are you attracted to them? Are you going to wait for them? Are they going to be the ones that lead us out of this time right now, or do you wait and sort of let them pick up a little bit?
```

**YOUR LABEL (F or N):** ______

### Row 106

```
PREV: ... with European powers. But the United States did not sign on, and the efforts fell apart. Iran began building thousands of centrifuges that are used to enrich uranium. Ali Vaez says the meaning of Iran's nuclear program was changing again. Iran had called the program a symbol of the corrupt West, but now made it a symbol of Iran's defiance.
GUEST: And this was really a new narrative, and it was around this narrative that a new sense of nationalism was created.
TARGET: Does your country, does your government that you represent, have any proposal that it can make that would reassure the world when it comes to uranium?
```

**YOUR LABEL (F or N):** ______

### Row 107

```
PREV: And so how would you see that playing out, Dov Zakheim?
GUEST: There is - as a matter of fact internal to the defense budget there is a problem that mirrors the growth of entitlements in the federal budget writ large. We have the same problem internal to the defense budget.
TARGET: Good.
```

**YOUR LABEL (F or N):** ______

### Row 108

```
PREV: But is there anything in Bashar al-Assad's profile that would suggest if he's able to hold onto power long enough to be part of a solution that then he just, you know, hops a plane for France and says you guys take care of it from now on?
GUEST: No, nothing at all, and that's precisely my point. You can achieve limited political objectives with support for the opposition and limited military force. But the ultimate political objective of regime change takes a lot more than we have been prepared to do.
TARGET: One last question. What would the messy solution you're talking about ideally look like in, say, six months?
```

**YOUR LABEL (F or N):** ______

### Row 109

```
PREV: Did the government simply fail to respond?
GUEST: I think a lot of analysts and a lot of folks in Kunduz are saying that, that the government failed to respond. Four, five months ago, they came very close to capturing the city. They took some of the suburbs of the city. And the government barely defended it, and it relied on militias - on very controversial militias to defend the city. So if they came so close to a major city for the first time in 14 years - a few months ago - why didn't the government send reinforcements? Why didn't the government launch clearance operations to push back the Taliban from the surrounding districts that were choking the city? That's where the questions are.
TARGET: Is there any way to know if perhaps the population of that city, or some large part of the population, sympathized with the Taliban side?
```

**YOUR LABEL (F or N):** ______

### Row 110

```
PREV: Now, the U.S. has made - has not been shy about calling Mugabe and Zimbabwe kind of rogue and outside of the interests of the U.S. What do you think the U.S. has at stake in this election?
GUEST: ... you know, discussions in the U.S. State Department using the term regime change after that term was actually placed on Iraq. We saw what happened in the case of Iraq. Regime change has led to disaster. Now when people hear regime change coming out of the State Department, there's a lot of worry about manipulation of processes, and so there is concern that the U.S. may not be playing fair, that there may be back-handed deals in which certain organizations are supported by the U.S., and these actually contribute to a climate of anxiety, where the U.S. and the U.K., even if they may be saying absolutely the right thing in this context, are not seen as really honest brokers.
TARGET: Now, briefly, what are the negotiations going on around that?
```

**YOUR LABEL (F or N):** ______

### Row 111

```
PREV: Yesterday we heard from a civil liberties advocate named Glenn Katon who took issue with the very idea of radicalization.
GUEST: The term radicalization isn't really defined and there have been some attempts to describe it that have been debunked.
TARGET: Peter Neumann, how do you define radicalization? You know, what's the demarcation between being very faithful and radical?
```

**YOUR LABEL (F or N):** ______

### Row 112

```
PREV: So what would be the point, given that the majority of the imports come from - what? - like, Brazil, Canada, Germany?
GUEST: Exactly. It really is designed to protect U.S. steel and U.S. aluminum. That's the theory. What we have learned over the years is that protectionism doesn't protect. Protectionism actually harms. And this is so much bigger than steel and aluminum because what we're doing is challenging the world trade system that we played an important part in bringing together. So that's a problem.
TARGET: Well, the president seems to agree with that. I mean, he said - he tweeted on Friday morning, for example. The president tweeted that, quote, "trade wars are good and easy to win." What is your response to that?
```

**YOUR LABEL (F or N):** ______

### Row 113

```
PREV: OK. Matt Tait is founder and CEO of Capital Alpha Security, a cybersecurity firm in Britain. And we reached him via Skype. Matt, thanks a lot.
GUEST: Thank you very much.
TARGET: And we should also note here that Kaspersky Lab, whose doubts about the hack that we cited, has its headquarters in Moscow.
```

**YOUR LABEL (F or N):** ______

### Row 114

```
PREV: Tell me about the Palestinian plan to go to the United Nations this fall to seek recognition for a state. The U.S. opposes this. Israel obviously opposes it. Walk me through the Palestinian thinking on this. Is it that we have nothing to lose and we might as well do it?
GUEST: No, it's not that. I think you just heard the president at AIPAC saying that the Palestinians' inclination to go to the United Nations is because of their impatience, frustration that the bilateral tract, the so-called peace process, did not produce the end of the Israeli military occupation and the establishment of a Palestinian state. The Palestinian leadership is responsible for its people. They have to deliver an end to the occupation. It is not the only option for us. We have said that repeatedly. The political process remains to be our first option, but you have to put that in a context that will succeed.
TARGET: That's Maen Rashid Areikat. He is the Palestinian Liberation Organization's ambassador to Washington. He joined me here in the studio. Ambassador Areikat, thank you so much for coming in.
```

**YOUR LABEL (F or N):** ______

### Row 115

```
PREV: Do you have any sense, Michelle, of what sort of stigma these women and girls may face if they do go back to their home communities?
GUEST: I think there's a very real danger that some of them may be shunned because it is assumed that any young girl who was held was raped. I have spoken with other young women who escaped from Boko Haram on their own, and they told me that they were not. But I must say I wondered. When I was looking at the very many children and babies who came in this new group, I did wonder whose children those were.
TARGET: Is there one story that you heard from the women at the refugee camp who've been rescued - one story that has really stuck with you about what they endured?
```

**YOUR LABEL (F or N):** ______

### Row 116

```
PREV: You're used to those, right?
GUEST: Exactly. I would say a big night in the city and state that made Donald Trump for him. But I agree with Margie that it's not something that's going to change the trajectory of either race.
TARGET: He said he was grateful to his home state.
```

**YOUR LABEL (F or N):** ______

### Row 117

```
PREV: So with all this tough rhetoric from President Trump, from Kim Jong Un, how do we get to the de-escalation that you're talking about?
GUEST: I think the key is you have both leaders - and the president has put a marker down. The president has made it clear we are not a paper tiger. He's made it very, very clear. It's coming from the top. I think North Korea - and North Korea knows this. It goes back to the first Gulf War in 1991. Those advisers to Kim Jong Un know what we did to Saddam Hussein in 1991 with the first Gulf War when they went into Kuwait. They saw U.S. capabilities. Well, our capabilities are much greater right now. So there's no question they know what our capabilities are. And North Korea is not suicidal.
TARGET: What role will China play? And what does the U.S. have to do to encourage China to play that role?
```

**YOUR LABEL (F or N):** ______

### Row 118

```
PREV: What do these documents tell us about the way ISIS works, the bureaucracy of the group?
GUEST: The documents give you a unique view into the way they think and their - the hierarchy works. They try to organize their recruitees, and they try to put them into specifications they can use and direct them. The documents show us more about their thinking and about the way they want to run their state rather than tell us more about the life of those people being cast there.
TARGET: Yeah. I think there's something very surprising about seeing, you know, sort of check this box if you're willing to be a suicide bomber; check this box if you, you know, have bomb-making skills. You know, I think these are very normal, you know, human resources tools being used for a group that, you know, isn't necessarily (laughter) something we would find in normal life. Was that surprising to you?
```

**YOUR LABEL (F or N):** ______

### Row 119

```
PREV: ... say they're looking for as many as three shooters, armed with what they described as long guns. The manhunt has shut down traffic and public transit across the city. For more on the situation, we have Stefan Kornelius on the line by Skype. He's with the Munich newspaper Suddeutsche Zeitung, and he is in Munich now. Welcome to the program.
GUEST: Well, thank you.
TARGET: What do you know about what happened today at the Olympia shopping center?
```

**YOUR LABEL (F or N):** ______

### Row 120

```
PREV: And is there anything you can do if you're a state that's losing a seat? I mean, can you fight this process?
GUEST: Not really. I mean, I think litigation is inevitable, but the Census Bureau and the Commerce Department have been very successful in defending their methodology. So these are almost certainly the final numbers. Now you just got to figure out how to deal with it.
TARGET: That's Tim Storey, senior fellow at the National Conference of State Legislatures. Tim, thanks so much.
```

**YOUR LABEL (F or N):** ______


---

## Provenance

- Sampling seed: **62**. Rebuild this exact sheet with
  `.venv/bin/python experiments/h6_part2_tranche.py`.
- Rows: **120**, drawn from **5268** model classifications over
  **88** confirmatory subjects; **60** subjects appear.
- Classifier: Gemma-4-31B-it, rubric hash (frozen) `053b96cba42ebf03d966db3c22fce2acde3a685d5b4cca9badd556ee248a24da`
- Classifier records: `results/stage2_confirm/h6_classify/records/classify.jsonl`
- Answer key (do not open until finished):
  `results/stage2_openended/h6_part2_key.json`
