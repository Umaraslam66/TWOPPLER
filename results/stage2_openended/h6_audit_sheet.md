# H6 classifier audit sheet

**What this is.** A machine read 120 interviewer turns and sorted each one into
one of two boxes. Your job is to sort the same 120 turns yourself, without
seeing what the machine said. Afterwards we compare. If we agree often enough,
the machine's labels get used in the H6 experiment. If we don't, the
instructions it was given get rewritten and we try again.

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
whoever is scoring it (rows marked `X` are dropped, and the gate needs at least
100 answered rows to count).

Text is cut to the same length the machine saw it, so `...` means words were
removed there. That is normal - judge what's shown.

## One thing to know before you start

The plan said this check should cover at least 10 different people. This sheet
covers **6**. That is not an oversight and nothing was left out: the
machine has only ever been run on the 6 development subjects,
because the rules keep every other subject untouched until this very check
passes. Running it on more people first would break that rule. To make up some
of the difference the sheet has 120 rows instead of the required 100.
Whether that is good enough to count is your call, and it gets written down
either way.

---

### Row 1

```
PREV: What options are open now for the United States to undertake this week, this month, if necessary?
GUEST: ... June as systematic crimes against humanity. And the main one is the shelling of populated areas not under regime control. The use of artillery, aircraft, even scud missiles to terrorize people in these urban areas and in these towns and villages - this is what's driving the humanitarian crisis. And this is what I think the United States really has to take a look at in terms of a response. The response may be timed to some ultimate finding about chemical weapons use but the danger is that the chemical weapons then can become a distractor here. What's really right in front of our face right now is a humanitarian catastrophe that is engulfing not only Syria but its neighbors.
TARGET: Ambassador Frederic Hof, who's now with the Atlantic Council. Thank you so much, sir, for coming in.
```

**YOUR LABEL (F or N):** ______

### Row 2

```
PREV: Were there very similar debates about civil liberties? About how far to go? About how much people had to change in order to battle this threat?
GUEST: ... new law which gave him colossal and sweeping powers. And this law - violently opposed by some members of the Senate - was nevertheless ran through. Pompey took these unprecedented powers and set a precedent, which was then followed by Julius Caesar a few years later. And I don't think that it's reading too much into the history of Rome to see in that parallels with America today. I'm not saying that America is going to go the same way as the Roman Republic, but it is interesting to see that the question posed at that time was whether you could be the world's sole military superpower and remain a functioning democracy in the way that you always had been.
TARGET: You just alluded to the Roman Senate, which might underline another basic way that people in modern times have looked back on the Roman Empire and tried to learn from it or be inspired by it. The United States has a Senate today.
```

**YOUR LABEL (F or N):** ______

### Row 3

```
PREV: Robert Harris is the author of “Imperium”, a novel of ancient Rome. Thanks for speaking with us.
GUEST: Been a pleasure. Thank you.
TARGET: And our conversations on the history behind our political debates continue all Thanksgiving week. Tomorrow, we'll hear the founding fathers' views of religion.
```

**YOUR LABEL (F or N):** ______

### Row 4

```
PREV: Well, this is...
GUEST: ...material goods.
TARGET: Well, it's been a long-running argument. Basically, one side holding that poor people committed crime, and the more poor people you had, the more crime you are going to have.
```

**YOUR LABEL (F or N):** ______

### Row 5

```
PREV: We just have a couple of minutes left, but even...
GUEST: Sure.
TARGET: ...on immigration, in Phoenix, where some politicians would have us believe illegal immigrants are holding box cutters to the throats of the citizenry, crime is way down.
```

**YOUR LABEL (F or N):** ______

### Row 6

```
PREV: And then we have two questions that go to what happens after Assad - again, from Charlie. Is fear of a strict Islamic replacement government preventing common united resistance? And then from Tana(ph), the question is: If Assad leaves, what could prevent Syria from the kind of terrible conflict between Sunni and Shia that occurred in Iraq? Ambassador Hof?
GUEST: ... who doubts the incompetence, the corruption and the brutality of this regime - no one. But there are still plenty of Syrians, mainly in Syrian minorities, Alawites, Christians and others who are worried about what comes next. And when some of these rebel fighters appear on cable television stations that are viewed widely in Syria, in places like Damascus, you know, frankly, the image they portray sometimes is a bit frightening to these folks. Deb alluded earlier to fewer and fewer people on the fence. This is true in terms of people having no illusions about the Assad family, but there are still plenty - there are still, I would suspect, millions of Syrians who worry about what's coming next.
TARGET: So...
```

**YOUR LABEL (F or N):** ______

### Row 7

```
PREV: They buy a lot of Iranian oil.
GUEST: That's right and other commercial relationships, as well. But they also have good reason to maintain good relation with us. And so basically they said they don't want to get in the middle of it. They'll go along with incremental pressure, as long as the rest of the international community is onboard but that they're not going to take tough measures really one way or the other.
TARGET: And the Russians prevailed upon the Iranians to send that spent fuel back to Russia. So there's actually a framework for this, but the truth is that that kind of a deal that the caller is suggesting won't work at this stage for the Iranians because they don't trust the United States. And until some measure of trust gets built into this relationship, the Iranians are not going to rely on the United States for the future of what they believe is important and necessary nuclear power.
```

**YOUR LABEL (F or N):** ______

### Row 8

```
PREV: They buy a lot of Iranian oil.
GUEST: That's right and other commercial relationships, as well. But they also have good reason to maintain good relation with us. And so basically they said they don't want to get in the middle of it. They'll go along with incremental pressure, as long as the rest of the international community is onboard but that they're not going to take tough measures really one way or the other.
TARGET: And Mike Shuster, from the Iranian point of view, lifting sanctions or avoiding sanctions that are coming up, as you mentioned from Europe, what's the carrot from Iran's point of view?
```

**YOUR LABEL (F or N):** ______

### Row 9

```
PREV: Yet it's also conceivable this newly elected president, in the absence of parliament, would name the committee to rewrite the constitution himself, no?
GUEST: ... military men running the show, are actually themselves, in the next few days, going to appoint a 100-person committee, which they believe will reflect the diversity and heterogeneity of Egypt. Because that was, of course, one of the problems with the two previous committees that the parliament chose. The parliament is dominated by Islamists. Secular, liberal and other forces accused them of stacking the committee in their favor and - to the detriment of liberals - Coptic Christians, women and so on. So I think the Supreme Council of the Armed Forces is likely to appoint a 100-person committee, which then again, of course, that also lacks some legitimacy - I think rightfully so - in the eyes of many.
TARGET: Here's a quote from an Egyptian human rights lawyer, Hossam Bahgat, quoted by the Associated Press: "The military placed all powers in its hands. The entire process has been undermined beyond repair. They now have the legislative and executive powers in their hands. There's a big likelihood the military-backed candidate, Shafiq, is going to win. It is a soft military coup that unfortunately many people will support out of fear of an Islamic takeover of the state."
```

**YOUR LABEL (F or N):** ______

### Row 10

```
PREV: Let's hear now from someone who will be voting tomorrow for the United Kingdom to remain in the European Union. Best-selling British novelist Robert Harris told us he will do so because he remembers life before the U.K. was a member.
GUEST: We were isolated. We needed the trade. We needed the diplomatic links. We needed a sense of being part of the continent. So that was what I grew up with. And in 1975, the last time there was a referendum, I cast my vote - the first vote of my life - in favor of remaining in the EU. And that - I think, because of that historic memory of what life was like outside it, I think we have to stay in.
TARGET: What has you in such a terrible mood right now.
```

**YOUR LABEL (F or N):** ______

### Row 11

```
PREV: Well, I thought I would only have a minute left.
GUEST: So I mean, I don't see the point of continuing this conversation.
TARGET: You thought the Security Council - if this was on the telephone, you could hang up, but you can't. There's still less than a minute. What about Hans Blix?
```

**YOUR LABEL (F or N):** ______

### Row 12

```
PREV: Afsane Bassir Pour of Le Monde, thank you.
GUEST: Thank you.
TARGET: And that being Kuwait, of course, which we talked about earlier on the program. There are other ways of considering the life of a woman at the United Nations conference. There was an international exhibition entitled "Progress of the World's Women."
```

**YOUR LABEL (F or N):** ______

### Row 13

```
PREV: We have a question here from Suzanne(ph), who asks: Do any of the guests have insights about Assad will leave Damascus to go to the Latakia region? This region has so far been spared the destruction that other areas have suffered. Ambassador Hof?
GUEST: I think there is probably a pretty good chance that that, ultimately, Assad and his family will move to that region, perhaps as a step toward moving abroad. But clearly, clearly, right now, his top priority is to retain control of Damascus. If he loses Damascus, he's finished, because he is basically of very marginal use to his own supporters once that happens.
TARGET: Let's take a question from Cindy in Lake Tahoe, California. Hi, Cindy.
```

**YOUR LABEL (F or N):** ______

### Row 14

```
PREV: And so where does that leave us? More blood, more civilian deaths on top of the 60,000 that have already taken place? Or could this speech galvanize the international community to a level that we haven't seen yet?
GUEST: I suspect, Ari - and I'm sorry to reach this conclusion - but I do suspect it means more blood. It means a protracted process. It means yet more combat on the ground. It means yet more regime attacks on bread lines, on populated areas. So we are going to see the casualty count mounting, I'm afraid.
TARGET: Less and less people are on the fence. I think you still can find some, but if you're on the fence, you probably left. Or the alternative is you're too poor to leave. It takes some resources to get out of the country, to pay the money to cross the border. So that has always been a bar to the very, very poor. But most people have made a decision one way or the other.
```

**YOUR LABEL (F or N):** ______

### Row 15

```
PREV: James, this week Secretary-General Annan said he's gotten calls, letters.
GUEST: The United Nations has been really, really excellent, it has to be said, on the Sudan question. Beginning with Kofi Annan, you know, and the 10th anniversary of the genocide. He actually asked for military intervention.
TARGET: You've got two seconds.
```

**YOUR LABEL (F or N):** ______

### Row 16

```
PREV: ... a few of those. We have one from Harvey(ph), who writes: Iran has as much right to nuclear arms as anyone else. Rhetoric is silly. We are the only country to have used nuclear weapons during war. When it comes to projecting power, we are not innocent. We need to learn to live with other nations on an equal footing.
GUEST: ... still think that there is a lot to worry about with a nuclear-armed Iran, even if they're not suicidal. After all, the United States wasn't suicidal during the Cold War, but we were willing to risk nuclear war a number of times in crises with the Soviet Union, and we came very close to a nuclear exchange. So I think similarly, a nuclear-armed Iran, you know, on top of all the threats I pointed out to you before of them being more aggressive, further proliferation, and the list goes on, that they would also be willing to risk nuclear in crises with Israel and crises with the United States, and any one of those would have the possibility of escalating.
TARGET: Let's let Matthew respond to the point that you just made, that even if there were a military strike at this point, if that has to be the solution - and again, Matthew, I think you're also - you're agreeing that a negotiated solution would be better. But if there had to be a military solution, Suzanne is saying that it would be very temporary, that the Iranians would be able to rebuild and get us back in this position again. What about that?
```

**YOUR LABEL (F or N):** ______

### Row 17

```
PREV: We just have a couple of minutes left, but even...
GUEST: Sure.
TARGET: Fifteen seconds.
```

**YOUR LABEL (F or N):** ______

### Row 18

```
PREV: ... has to be the solution - and again, Matthew, I think you're also - you're agreeing that a negotiated solution would be better. But if there had to be a military solution, Suzanne is saying that it would be very temporary, that the Iranians would be able to rebuild and get us back in this position again. What about that?
GUEST: ... almost certain the United States would completely destroy Iran's key nuclear facilities. This would, at a minimum, set Iran's nuclear program back. But, of course, the hope would be that something happens to where Iran ends up permanently without nuclear weapons. And there are examples in the past, for example, Syria bombed - I'm sorry - Israel bombed a nuclear reactor in Syria in 2007, and there are no indications that Syria has rebuilt its nuclear facility since then. So it's possible that Iran could simply give up in the aftermath of a strike. But there's a lot that could happen with that additional time to where we end up in a situation where Iran is permanently without nuclear weapons.
TARGET: I think both of our guests are - understand deterrent as being part of containment, but how are you making the distinction?
```

**YOUR LABEL (F or N):** ______

### Row 19

```
PREV: And then we have two questions that go to what happens after Assad - again, from Charlie. Is fear of a strict Islamic replacement government preventing common united resistance? And then from Tana(ph), the question is: If Assad leaves, what could prevent Syria from the kind of terrible conflict between Sunni and Shia that occurred in Iraq? Ambassador Hof?
GUEST: ... who doubts the incompetence, the corruption and the brutality of this regime - no one. But there are still plenty of Syrians, mainly in Syrian minorities, Alawites, Christians and others who are worried about what comes next. And when some of these rebel fighters appear on cable television stations that are viewed widely in Syria, in places like Damascus, you know, frankly, the image they portray sometimes is a bit frightening to these folks. Deb alluded earlier to fewer and fewer people on the fence. This is true in terms of people having no illusions about the Assad family, but there are still plenty - there are still, I would suspect, millions of Syrians who worry about what's coming next.
TARGET: And so, Ambassador Hof, I guess the overarching question is: With 60,000 people dead in Syria already, at what point does the U.S. say, enough? We have to marshal all of our resources to make sure this ends.
```

**YOUR LABEL (F or N):** ______

### Row 20

```
PREV: All right. We have to move on to another very sticky issue on the agenda this week, which is the observer force in the Middle East. And, James, what's your reaction to the secretary-general's effort on that part?
GUEST: Actually, that's was a breakthrough, the fact-finding mission by Mitchell that James just mentioned because the Israelis were against that also. But they left the door open, not only to the mission that is going to go and also this idea of Kofi Annan, that rather than go to the Security Council and vote for an observer force, just put in a few observers into this commission so that at least there's somebody from the outside looking to see what's happening. That's what Kofi's working on and the Israelis seem to be - at least the Israelis in New York seem to be, you know, opening the door just slightly.
TARGET: Wait, James. While we're on the subject of unofficial permission, let's talk about the Jordanian flights to Iraq, those done without any "mother may I" from the UN also.
```

**YOUR LABEL (F or N):** ______

### Row 21

```
PREV: Let's get Paula(ph) on the line. Paula calling us from Bend, Oregon.
GUEST: Well, I'm...
TARGET: Go ahead.
```

**YOUR LABEL (F or N):** ______

### Row 22

```
PREV: Right.
GUEST: ... They were largely youth and secular groups in addition to the anti-Mubarak (unintelligible) Mubarak group and then the National Association of Change, the Mohamed ElBaradei group. But with regard to imagining a government that would be in charge of shepherding Egypt into free and fair elections for genuine reform to take place, there are many individuals in the country. The minister of industry is very well-respected, and I don't believe he's a member of the ruling party -along with figures like Mohamed ElBaradei, of course, along with the head of the Wafd, an opposition party. I think they could form some kind of an interim government that could shepherd Egypt until there are free and fair elections in the future.
TARGET: That's Samer Shehata. He's a professor of Arab politics at Georgetown University.
```

**YOUR LABEL (F or N):** ______

### Row 23

```
PREV: And, of course, your wife is - I believe, works at CNN. James, I think you had a parental question before we get into the hard news.
GUEST: Jamie, everybody knows that you're much more than a spokesman. You were Secretary Albright's closest adviser, in fact. What are you going to miss most about leaving this job?
TARGET: You're going to also be without Madeline Albright. And as we look back in our library of videotape, you see her standing next to you at the Security Council stakeout position, and from New York to around the world, you were always there, even whispering in her ear many times right before she would say something. What are you going to miss about her, and who really was the power here? A lot of people always had questions about that.
```

**YOUR LABEL (F or N):** ______

### Row 24

```
PREV: It's fair to say, Matt Kroenig, the United States doesn't quite trust Iran, either.
GUEST: There's a lot of mistrust on both sides. And I think I would agree with the caller that that's a good way forward. In fact, that's something that we've tried in the past, but Iran has been unwilling to accept those fuel assurances from outside. Iran's explanation is that it wants the ability to produce fuel itself for energy security purposes. But I think many people, including myself, suspect that it's - Iran wants the nuclear weapons capability that comes with the ability to produce fuel indigenously.
TARGET: It is scheduled one day. Of course, they can always come out in the first day and say we're going to stay here in Baghdad and do a second day. I think that's what happened in Istanbul last month. That would be a positive sign if there is a suggestion that there is more to talk about rather than less. Even if it stays at just one day of talks, if they come out of it and say we're going to meet again within the next week or next couple weeks or next month - again, another positive sign.
```

**YOUR LABEL (F or N):** ______

### Row 25

```
PREV: They buy a lot of Iranian oil.
GUEST: That's right and other commercial relationships, as well. But they also have good reason to maintain good relation with us. And so basically they said they don't want to get in the middle of it. They'll go along with incremental pressure, as long as the rest of the international community is onboard but that they're not going to take tough measures really one way or the other.
TARGET: Gary Sick is a senior research scholar at Columbia University's Middle East Institute. Also with us, NPR diplomatic correspondent Mike Shuster and Matthew Kroenig, who's a Stanton national security fellow at the Council on Foreign Relations. You're listening to TALK OF THE NATION coming to you from NPR News. Let's get Gary(ph) on the line. Gary with us from Delray Beach in Florida.
```

**YOUR LABEL (F or N):** ______

### Row 26

```
PREV: Talk a little bit about what happens now. I mean, we know that the military is in charge. What happens next?
GUEST: ... take place, but elections under the previous constitution would really be deformed elections because of the amendments that really limit full participation. So elections, but not necessarily in 60 days, for example, as what the present constitution stipulates, what we've seen as an extra constitutional move on the part of the higher military counsel, right? It's not following the letter of the constitution. So I think the constitution is in abeyance for now and we're gonna have to see what happens. I would hope an interim government, certainly. We don't want people in uniforms running the affairs of state for any length of time. And hopefully, that interim government would be composed of a wide variety of respected known individuals.
TARGET: Samer, obviously, a lot of the faces we've seen on television are young faces. These are young people who have known nothing except Hosni Mubarak. They have lived under no other leadership, no other system of government. They've lived primarily under an emergency law for most of their lives. I mean, how are they going to sort of know what to do, I guess?
```

**YOUR LABEL (F or N):** ______

### Row 27

```
PREV: But let me ask you, Samer Shehata, 30 years in power, Mr. Mubarak must have some supporters.
GUEST: ... of whom fled the country yesterday or two days ago on private jets, including the hated Ahmed Ezz, a steel mogul, and also one of the people in charge of the ruling party. So there were some people who were in charge who supporting Mubarak. But the point is that, over the last 25 years or so, the bases of the regime have changed. They have shed workers, they have shed farmers, they have shed civil society, middle-class people as bases of support because of the elimination of subsidies and privatization and so on. And they have taken, instead, large capital as the basis of support, in addition to the military and, of course, the foreign backers, the international community.
TARGET: But I think if it does happen, you know, like I said earlier, I think we're in a moment of flux here. This is a - it's a pivotal moment. I know the word is overused in events like these, but it does feel, it does feel like things are very undecided and very much in transition.
```

**YOUR LABEL (F or N):** ______

### Row 28

```
PREV: Professor Shehata, thanks a lot for talking with us.
GUEST: You're welcome. Nice speaking with you.
TARGET: Samer Shehata, assistant professor of Arab politics at Georgetown University's School of Foreign Service.
```

**YOUR LABEL (F or N):** ______

### Row 29

```
PREV: Interestingly enough, the Muslim Brotherhood, which is presumably the largest opposition in Egypt now, does not want to postpone those elections. They want to go ahead and go forward with them. Is that because they're assuming that they are going to win big?
GUEST: That's right. They've been campaigning very well and they feel that they're going to do well in these elections. And that is how they're going to better their position politically in the political process.
TARGET: If the Muslim Brotherhood does gain a majority in these in these parliamentary elections, does that then set them up for a confrontation with the military council?
```

**YOUR LABEL (F or N):** ______

### Row 30

```
PREV: It's fair to say, Matt Kroenig, the United States doesn't quite trust Iran, either.
GUEST: There's a lot of mistrust on both sides. And I think I would agree with the caller that that's a good way forward. In fact, that's something that we've tried in the past, but Iran has been unwilling to accept those fuel assurances from outside. Iran's explanation is that it wants the ability to produce fuel itself for energy security purposes. But I think many people, including myself, suspect that it's - Iran wants the nuclear weapons capability that comes with the ability to produce fuel indigenously.
TARGET: Saed, I'm sorry. I don't mean to cut you off. We just have a few seconds left. Get to your point, please.
```

**YOUR LABEL (F or N):** ______

### Row 31

```
PREV: ... I don't think he looks good where the statement - the letter comes out in the next few days. You have suicide bombings. It just looks unfair.
GUEST: Yes, he's kind of slipped a little bit, I agree with James, both on Iraq and on the Middle East.
TARGET: ... to the Palestinians. Let's talk about human rights. Why not? Mary Robinson, both of you previewed her exit. "The New York Times" said it was unexpected, but if you watched our show, you knew it was coming. Mary Robinson will be leaving her term as the U.N. Human Rights Chief. The group Human Rights Watch was very disappointed with the Robinson exit. The group thinks she stood up to the bullies, now who will follow?
```

**YOUR LABEL (F or N):** ______

### Row 32

```
PREV: I think she had it that the world is a mess. And of course, that trip goes to right what we're talking about here. Congo and Sierra Leone, future peacekeeping missions. Very brief.
GUEST: You know, one of the people who was there was the Algerian, Lakhar Brahimi, and he told me that they basically talked about lessons learned from Sierra Leone. Mr. Brahimi is charged with writing a very vast, comprehensive report about peacekeeping operations in general and what can be done about them. That is expected end of July. So that was a big subject of discussion.
TARGET: Afsane Bassir Pour of Le Monde, thank you.
```

**YOUR LABEL (F or N):** ______

### Row 33

```
PREV: And therefore provide more time for talks.
GUEST: ... China are very unlikely to go along with additional Security Council resolutions. So that's not much of a benefit for Iran. And the United States has also talked about possibly providing fuel for this Tehran Research Reactor if Iran is willing to ship out the 20 percent. But we've offered similar things in the past, and Iran has not been willing to accept that, which suggests that they want the ability to enrich the uranium themselves, not necessarily just the fuel for the reactor. So I'm skeptical that the talks are going to produce concrete results not because the United States doesn't want them but because it's not clear what Iran gets out of an agreement with the United States.
TARGET: There's also, as you mentioned, divisions among this group called P5+1, that's the five permanent members of the Security Council - the United States, Britain, France, China and Russia - plus Germany. And those divisions are evident, as you said. Russia and China would be highly skeptical of more sanctions at the Security Council. In the past, Iran has also tried to drive wedges in between those various different groups.
```

**YOUR LABEL (F or N):** ______

### Row 34

```
PREV: Mr. Harris, thanks so much for talking to us. We appreciate it.
GUEST: Oh, it's been a pleasure. Thank you.
TARGET: That was the British writer Robert Harris, who is a remainer. He will be voting for the United Kingdom to remain in the European Union tomorrow.
```

**YOUR LABEL (F or N):** ______

### Row 35

```
PREV: Joining us in the studio is Samer Shehata, an assistant professor of Arab politics at Georgetown University. Nice to have you with us today.
GUEST: Thank you.
TARGET: And also with us from Cairo is the correspondent of the New York Times, Anthony Shadid. Anthony Shadid, good to have you back on TALK OF THE NATION.
```

**YOUR LABEL (F or N):** ______

### Row 36

```
PREV: Lot of pressure to lift sanctions, though, on this regime. You know, the people there are suffering. We've had debates, that's what Afsane was referring to, here on the show. I think it's something James and you might agree on, actually, but.
GUEST: Well, there is already a tilt towards Iran.
TARGET: On Libya, the families are outraged. They say Secretary Albright has sold them out, that you're going to soon lift the air travel ban on Americans traveling to Libya even before this trial is finished. What's your response?
```

**YOUR LABEL (F or N):** ______

### Row 37

```
PREV: The Copts, of course, are a Christian sect that have been in Egypt for thousands of years, and their numbers of the population -correct me if I'm wrong - some are Shiatists - something about 10 to 15 percent of the population.
GUEST: That's exactly correct.
TARGET: And what about the - is there a voice for them in these uprisings?
```

**YOUR LABEL (F or N):** ______

### Row 38

```
PREV: And where does this leave the secular Egyptians - who a lot of people gave credit for starting all of this back, what, 16, 18 months ago - where does it leave them? They were given the choice between an authoritarian, Mr. Shafiq, and a member of the Muslim Brotherhood.
GUEST: ... liberals and secular forces, are really having a difficult time right now. They see the choice in front of them as between worse and terrible. And some are holding their nose and voting, or going to vote for the Muslim Brotherhood candidate, because he represents some kind of change. Others who prioritize the idea of a secular state or a civil state are holding their nose and going to choose Shafiq, Mr. Mubarak's last prime minister. And a significant number of them have actually called for either a boycott of the election, or going and voting and invalidating their votes. And we've already seen significant numbers of that in the expatriate voting that has already taken place across the world.
TARGET: Samer Shehata, thank you very much for your time today. Appreciate it.
```

**YOUR LABEL (F or N):** ______

### Row 39

```
PREV: ... flap that Bill Cosby caused by, some people say, suggested blaming the victim, if you will. There will be others that will say that's the same kind of thought there. Yet there is a need for communities to truly take a hard look at what's going on within their boundaries. In your studies, have you seen that happening of late?
GUEST: ... distinct problem. So what we have is a new generation of kids, an increase in kids, yet it's not random, it tends to be this concentration of poverty that we need to pay attention to. And I would add that today's 16-, 17-, 18-year-olds, which is at the peak of a violence curve, were born to parents at the height of the crack cocaine epidemic and rampant violence in the late '80s and early '90s. So there's a lot of complicated factors going on here. And I don't think that identifying some of these fundamental facts is really blaming the victim. It's more targeting where the social issues are likely to occur in trying to think creatively about effective solutions.
TARGET: Reverend Rivers, what about talking about the influx of drugs into the community, gang activity, the chronic unemployment that sits in many of these communities, and the pop culture of thug life, if you will, that is pervasive among young black men. How do you deal with that?
```

**YOUR LABEL (F or N):** ______

### Row 40

```
PREV: ... flap that Bill Cosby caused by, some people say, suggested blaming the victim, if you will. There will be others that will say that's the same kind of thought there. Yet there is a need for communities to truly take a hard look at what's going on within their boundaries. In your studies, have you seen that happening of late?
GUEST: ... distinct problem. So what we have is a new generation of kids, an increase in kids, yet it's not random, it tends to be this concentration of poverty that we need to pay attention to. And I would add that today's 16-, 17-, 18-year-olds, which is at the peak of a violence curve, were born to parents at the height of the crack cocaine epidemic and rampant violence in the late '80s and early '90s. So there's a lot of complicated factors going on here. And I don't think that identifying some of these fundamental facts is really blaming the victim. It's more targeting where the social issues are likely to occur in trying to think creatively about effective solutions.
TARGET: Indeed, that is...
```

**YOUR LABEL (F or N):** ______

### Row 41

```
PREV: Talk more about what we hear from Assad in this speech on Sunday.
GUEST: I think the principal thing we heard from President Assad, and I suspect the main reason why he did this was to rally the troops. Bashar al-Assad has attempted to implicate a major part of Syria's population in the methodology he has used to try to perpetuate family rule in Syria.
TARGET: What do you mean by that?
```

**YOUR LABEL (F or N):** ______

### Row 42

```
PREV: And so where does that leave us? More blood, more civilian deaths on top of the 60,000 that have already taken place? Or could this speech galvanize the international community to a level that we haven't seen yet?
GUEST: I suspect, Ari - and I'm sorry to reach this conclusion - but I do suspect it means more blood. It means a protracted process. It means yet more combat on the ground. It means yet more regime attacks on bread lines, on populated areas. So we are going to see the casualty count mounting, I'm afraid.
TARGET: That really hasn't happened. It's only a trickle now. So to try to put together a local government without resources is not an easy thing to do.
```

**YOUR LABEL (F or N):** ______

### Row 43

```
PREV: But let me ask you, Samer Shehata, 30 years in power, Mr. Mubarak must have some supporters.
GUEST: ... of whom fled the country yesterday or two days ago on private jets, including the hated Ahmed Ezz, a steel mogul, and also one of the people in charge of the ruling party. So there were some people who were in charge who supporting Mubarak. But the point is that, over the last 25 years or so, the bases of the regime have changed. They have shed workers, they have shed farmers, they have shed civil society, middle-class people as bases of support because of the elimination of subsidies and privatization and so on. And they have taken, instead, large capital as the basis of support, in addition to the military and, of course, the foreign backers, the international community.
TARGET: And several people I talked to actually made that point. That just before this uprising happened, they felt that they were the lowest points of their lives. They're looking for visas to other countries. They didn't feel part of this country. They didn't feel part of the society itself. And I think this is what - when you use the word revolution, I think this is what you notice on the streets today is people are taking ownership again of this country.
```

**YOUR LABEL (F or N):** ______

### Row 44

```
PREV: ... with you. We heard from Phillip Martin the idea, if you will, of the changing of America, to a great degree the browning of America, being just one--and I underline just one--of the problems that we are seeing in terms of the escalation of violent crime, particularly murder in this country. There are so many contributing factors, though, aren't there?
GUEST: ... standing of the city. That said, there's certainly an increase and certainly a problem. I would be hesitant to blame it all on immigration. In fact, in terms of national statistics, immigration seems to be, if anything, related to lower rates of crime and violence. And some of our most diverse cities with exploding immigrant populations--Los Angeles, Chicago metropolitan area and others--again are experiencing decreases. So it is a complicated picture and one can't point to any single factor like that. And in fact I think the immigration finding is something that needs to be re-enforced because it can lead to stereotypes that suggest that specific race or ethnic groups are somehow inherently more likely to be involved in violence.
TARGET: Robert Sampson, let me ask you, in relation to what Reverend Rivers just suggested, we saw the flap that Bill Cosby caused by, some people say, suggested blaming the victim, if you will. There will be others that will say that's the same kind of thought there. Yet there is a need for communities to truly take a hard look at what's going on within their boundaries. In your studies, have you seen that happening of late?
```

**YOUR LABEL (F or N):** ______

### Row 45

```
PREV: Business contracts were good to go in.
GUEST: On the other side, the Americans focused on smuggling, which has become a big deal, not just in the Iraq context, but because the oil prices are rising.
TARGET: There's a lot more smuggling. James, the vice admiral was here - big time guy - the coordinator of the forces there in the Gulf.
```

**YOUR LABEL (F or N):** ______

### Row 46

```
PREV: The Alawites.
GUEST: ... beginning of his father's regime in 1970, a key regime objective has been to try to prevent rival power centers from growing within the Alawite community. Going back to the time of the French in the early part of the 20th century, Alawites have been recruited in large numbers to the Syrian military and other security forces. So it's an important minority group. It is a minority group that has not really benefitted in any substantial way from the rule of the Assad family. It is still the poorest group in the country. But it's important for Assad to maintain unity and to - among them, and to make sure nobody thinks that he's about to bolt for greener pastures.
TARGET: So going back to this specific speech on Sunday, why, after six months of being silent and absent from the spotlight, would - at this moment - he feel the need to rally the troops in a way that you're describing?
```

**YOUR LABEL (F or N):** ______

### Row 47

```
PREV: Robert Harris is reading from his book, “Imperium,” which is a novel about the Roman Empire. And if you think this language sounds like a description of a modern war, consider this quote that Mr. Harris attributes to a famous Roman general.
GUEST: (Reading) “Any ruler who refuses to cooperate will be regarded as Rome's enemy. Those who are not with us are against us.”
TARGET: Robert Harris, you're writing a fictional account of the Roman Empire, but based on real events. Why, when you're looking at events from 2,000 years ago, draw such an exact parallel with what's happening today?
```

**YOUR LABEL (F or N):** ______

### Row 48

```
PREV: Professor Bone.
GUEST: Accept the inspectors.
TARGET: James.
```

**YOUR LABEL (F or N):** ______

### Row 49

```
PREV: Ambassador Hof, as a former State Department official, can you reflect on any of this?
GUEST: ... late in the term of President Assad's father, Hafez al-Assad, when there were some very serious and detailed discussions about the contours of a possible peace agreement between Israel and Syria. That process collapsed right around the time of President Hafez al-Assad's death. And when Bashar al-Assad took over as president, it took a while for any kind of relationships to begin to mature. I would sum it up like this: Yeah, I think President Bashar al-Assad was certainly interested in having a cordial, productive relationship with the United States, certainly a relationship without any economic sanctions or any of that business, but was never really willing to do what it would take to have that kind of a relationship.
TARGET: Surface-to-surface appears to be not armed with chemical weapons. I think we would have heard something about that by now. And they seem to be more accurate over time. There was a report in the New York Times and other outlets that these are Iranian-made missiles, and he has been using those over the past couple of weeks.
```

**YOUR LABEL (F or N):** ______

### Row 50

```
PREV: My understanding is that if it is deployed, there is very little time to respond.
GUEST: There is very little time to respond, and I - you know, I suspect, you know, going back to the initial point, Ari, about why the speech, what President Assad was saying, the chemical element of this weighs in the equation, because on the one hand, you have Assad saying the situation is well in hand. I'm dealing with a handful of foreign terrorists with foreign masters. I'm going to dominate this situation. We're going to win. And on the other hand, he's willing to contemplate the absolutely desperate measure of using chemical munitions against his own people. So there is a basic contradiction there.
TARGET: And we have an email question from Steve in Minneapolis, who writes: What are Assad's options, and what are the options for the Alawite population?
```

**YOUR LABEL (F or N):** ______

### Row 51

```
PREV: Samer Shehata, too little, too late?
GUEST: ... much too little, much too late. And I think that as Anthony said, things have changed between Friday and between last week and now. And what we're hearing from people in many parts of Egypt, including in Tahrir, is that now they want not only for the president to step down, but they want to try the president. They want to hold him accountable, not just for the last 29 years of autocratic rule, but for the incredible damage that has been done to Egypt and the loss of life over the last week. There have been over 150 people who have been killed. There has been tremendous damage to infrastructure. And most people place the responsibility with President Mubarak.
TARGET: Are you hearing me?
```

**YOUR LABEL (F or N):** ______

### Row 52

```
PREV: ... Israel formally notified the United Nations that it intends to pull out from southern Lebanon on July 7. The Israeli ambassador to the UN handed over a letter to that effect to Secretary-General Annan. Afsane, the Security Council then was told by Annan about this and now is telling Annan what? And what's going to happen now regarding the pullout?
GUEST: ... of the UN in the region, in southern Lebanon is called UNIFIL, which is United Nations Interim Force. They've been there for 20 years, now - 22 years, in fact - since 1978. And now, they'll be doing, finally, what they were created to do after 22 years, but it's a very difficult mandate and the secretary-general, rightly so, is very, very worried. Not only have they to verify the withdrawal of the Israeli forces, they have to - they have three things to do. One of them is bring peace and security to the region. I mean, that's a long list. And then the third thing is to restore Lebanon's authority - government of Lebanon's authority over the country.
TARGET: Because they might have to call Damascus. James?
```

**YOUR LABEL (F or N):** ______

### Row 53

```
PREV: Well, it's been a long-running argument. Basically, one side holding that poor people committed crime, and the more poor people you had, the more crime you are going to have.
GUEST: ... segregation, isolation of groups that are poor, in poor schools, then we do see higher rates of not only violence but school dropout and a number of other social problems. So it's fairly complex. But I think the simple dynamic or over-time relationship between crime and economy, which is what most people fixate on, simply does not work all that well. And that's why the usual suspect is part of the explanation, because people assume, well, a bad thing has happened, economy has gone down, and therefore crime should go up. But we tend not to think about some of the other characteristics that drive crime variations over time, such as incarceration and policing, age structure, immigration, and so forth.
TARGET: The other theory broadly held - that no, poor people don't commit crime, criminals commit crimes. And the more criminals you lock up and put away, the fewer crimes you're going to have.
```

**YOUR LABEL (F or N):** ______

### Row 54

```
PREV: And so where does that leave us? More blood, more civilian deaths on top of the 60,000 that have already taken place? Or could this speech galvanize the international community to a level that we haven't seen yet?
GUEST: I suspect, Ari - and I'm sorry to reach this conclusion - but I do suspect it means more blood. It means a protracted process. It means yet more combat on the ground. It means yet more regime attacks on bread lines, on populated areas. So we are going to see the casualty count mounting, I'm afraid.
TARGET: You described kind of the horrific experience of waiting in a bread line for hours, wondering if a bomb is going to fall on you. Tell us more about what daily life is like for people who are still in Syria.
```

**YOUR LABEL (F or N):** ______

### Row 55

```
PREV: Twenty-one - I was trying to remember...
GUEST: Yes. That's exactly correct. And of course, you know, President Mubarak handled those kinds of issues abysmally. He handled those kinds of issues by repression, by repressing political space, by repressing all opposition groups, including the Muslim brotherhood. But I think it is fair to say now that the groups that have been organizing these protests and the people who have been participating them well beyond the membership of these groups represent a huge segment of Egyptian society - Christians, as well as Muslims.
TARGET: Nora, thank you very much for the call. We appreciate it.
```

**YOUR LABEL (F or N):** ______

### Row 56

```
PREV: ... has to be the solution - and again, Matthew, I think you're also - you're agreeing that a negotiated solution would be better. But if there had to be a military solution, Suzanne is saying that it would be very temporary, that the Iranians would be able to rebuild and get us back in this position again. What about that?
GUEST: ... almost certain the United States would completely destroy Iran's key nuclear facilities. This would, at a minimum, set Iran's nuclear program back. But, of course, the hope would be that something happens to where Iran ends up permanently without nuclear weapons. And there are examples in the past, for example, Syria bombed - I'm sorry - Israel bombed a nuclear reactor in Syria in 2007, and there are no indications that Syria has rebuilt its nuclear facility since then. So it's possible that Iran could simply give up in the aftermath of a strike. But there's a lot that could happen with that additional time to where we end up in a situation where Iran is permanently without nuclear weapons.
TARGET: I mean, the reason we're talking about this and this sense of urgency comes now is because the Israelis are concerned that the clock is ticking and a window is closing for them to do something about this because the Iranians are apparently beginning to put stuff underground, and it will soon be out of reach of Israeli bombs, some of it will be. And the Israelis missed their opportunity to do something once - what they would think of as once and for all, taking still the point you make, Suzanne, that they might be able to rebuild. But given that ticking clock situation, I want to ask you, Matthew, is there any indication at all - since both ...
```

**YOUR LABEL (F or N):** ______

### Row 57

```
PREV: Well, Secretary-General Annan met with the Israeli foreign minister in Geneva, and there will be continuing dialog, right? The Israelis are up front.
GUEST: Yeah. Actually, the UN is very worried about this. I mean, there's nothing they can do. They have to get involved, but they're very worried because, for example, the Lebanese are now saying the UN should disarm the Palestinians. You know, they're about, what, 40,000-50,000 Palestinians, most of them armed. And the UN doesn't want to get into the business of disarming anybody. So there's lots of things to be solved. But there's a real, real worry within the UN about the prospects of this particular operation.
TARGET: And the focus will be on resolutions from the Security Council 425-426, which dealt with the pullout back in the late `70s. Both of our guests will stay on, hopefully. The mayor of New York City, who everybody here lives under, is in a political contest for the United States Senate with the first lady of the United States, Hillary Rodham Clinton, who is an advocate of the United Nations. While recently, the mayor has not been so enthusiastic, unlike Ms. Clinton, during the diplomatic license plate war, you may remember a few years ago, Mayor Guiliani said, "If they'd like to leave New York over parking tickets, we can find another use for that area of town." He also ...
```

**YOUR LABEL (F or N):** ______

### Row 58

```
PREV: Twenty-one - I was trying to remember...
GUEST: Yes. That's exactly correct. And of course, you know, President Mubarak handled those kinds of issues abysmally. He handled those kinds of issues by repression, by repressing political space, by repressing all opposition groups, including the Muslim brotherhood. But I think it is fair to say now that the groups that have been organizing these protests and the people who have been participating them well beyond the membership of these groups represent a huge segment of Egyptian society - Christians, as well as Muslims.
TARGET: With us here in the studio in Washington is Samer Shehata, assistant professor of Arab politics at Georgetown University. And let's see if we can get some more calls in on the conversation. Let's go next to Al, and Al is with us from San Antonio.
```

**YOUR LABEL (F or N):** ______

### Row 59

```
PREV: And this is going to be the key part of the discussions in Washington where, Afsane, the entire Security Council goes on Thursday to meet with Senator Helms, the Senate Foreign Relations Committee and U.S. officials, right?
GUEST: Well, Richard, you know I've been away for two weeks, and for me, the most extraordinary development is that the Security Council has accepted Jesse Helms' invitation to go to Washington. To me, it's like Security Council going to the Roman Empire to pay homage. I remember the day Jesse Helms made the invitation. Everybody was saying this is ludicrous.
TARGET: Well, I don't think that all of us were.
```

**YOUR LABEL (F or N):** ______

### Row 60

```
PREV: ... a few of those. We have one from Harvey(ph), who writes: Iran has as much right to nuclear arms as anyone else. Rhetoric is silly. We are the only country to have used nuclear weapons during war. When it comes to projecting power, we are not innocent. We need to learn to live with other nations on an equal footing.
GUEST: ... still think that there is a lot to worry about with a nuclear-armed Iran, even if they're not suicidal. After all, the United States wasn't suicidal during the Cold War, but we were willing to risk nuclear war a number of times in crises with the Soviet Union, and we came very close to a nuclear exchange. So I think similarly, a nuclear-armed Iran, you know, on top of all the threats I pointed out to you before of them being more aggressive, further proliferation, and the list goes on, that they would also be willing to risk nuclear in crises with Israel and crises with the United States, and any one of those would have the possibility of escalating.
TARGET: What are the implications of another war in the Middle East that would make - I want to put this also, after you answer the question, to Matthew. What are the implications of a war in the Middle East that to you I think would make a containment policy preferable to the results of a war in the Middle East?
```

**YOUR LABEL (F or N):** ______

### Row 61

```
PREV: Liberia.
GUEST: .Liberia, next door. And apparently, his country is selling 200 times more diamonds than it can produce. So obviously, there's a link. But for the first time, they're beginning to address that. Very interesting.
TARGET: James, when do the British say they're pulling out of there?
```

**YOUR LABEL (F or N):** ______

### Row 62

```
PREV: Yes, I mean.
GUEST: But don't you think, symbolically.
TARGET: They need each other.
```

**YOUR LABEL (F or N):** ______

### Row 63

```
PREV: ... for Middle East Policy at the Brooking Institution, and Matthew Kroenig, Stanton Nuclear Security fellow at the Council on Foreign Relations. As we say, the clock is ticking on this issue, but there's still time to go, so I'm assuming, almost certain, we'll be returning to this topic in the future. But thank you for joining us, both of you.
GUEST: Thank you.
TARGET: And thank you to our listeners for your calls. Coming up, we talked last week about the frustration and the guilt felt by many adult children who find themselves taking care of their aging parents. Today, we're going to hear from the other side. We're going to hear from the point of view of those aging parents. I'm John Donvan. This is TALK OF THE NATION from NPR News.
```

**YOUR LABEL (F or N):** ______

### Row 64

```
PREV: .of smart sanctions, right.
GUEST: That's right.
TARGET: And you've talked about them.
```

**YOUR LABEL (F or N):** ______

### Row 65

```
PREV: By families, I mean the families of those killed on Lockerbie Pan Am 103.
GUEST: Jamie, now that you're leaving, maybe you can finally tell us - is it true that you played a crucial role in getting rid of Boutros Boutros-Ghali?
TARGET: The previous secretary of state of the UN - secretary- general of the United Nations.
```

**YOUR LABEL (F or N):** ______

### Row 66

```
PREV: The other theory broadly held - that no, poor people don't commit crime, criminals commit crimes. And the more criminals you lock up and put away, the fewer crimes you're going to have.
GUEST: ... that. We have to look to broader factors, which is why I think that social conditions, particularly the great changes that we've seen in immigration, have something to do with it. And also that has something to do with the question you posed at the beginning, or the paradox: Why do people perceive there to be a difference in the crime rate? That is, they think it's really going up by a lot. I mean, 75 percent of the population think it's going up. That's a substantial number. And it went up from about 50 percent, I believe it was, in a Gallup poll from a few years back. So that's a trend that's directly opposite to what's really happening.
TARGET: Robert Sampson is our guest, chairman of the Department of Sociology and professor of social sciences at Harvard. You're listening to TALK OF THE NATION from NPR News.
```

**YOUR LABEL (F or N):** ______

### Row 67

```
PREV: ...you're talking about, not commercial flights.
GUEST: ... in saying that the United States is the only country that is allowed to have its nuclear vessels pass through the Suez Canal, or something like the blockade of Gaza. Now, right now, Egypt is participating in essentially a blockade of 1.5 million people in Gaza, not allowing anything to go into the area, and so. I can't imagine that if the Egyptian people had their way that that would be the policy. I'm not saying that they would, you know, support Hamas or give them weapons, no. But I think that they will allow commodities, everything from, you know - from gasoline to diapers - to be allowed to go into Gaza. So those were some of the differences.
TARGET: And we've heard, Samer Shehata, obviously about Tunisia, still protests in Algeria. We've heard about Jordan, again, King Abdullah today dismissed his prime minister and his cabinet in response to demonstrations there. But a lot of people wonder, Saudi Arabia, the world's largest oil exporter, what is going on there?
```

**YOUR LABEL (F or N):** ______

### Row 68

```
PREV: And that came a few weeks after the French troops were criticized for inaction in Mitrovica. Afsane?
GUEST: ... James says. Louise Arbour, the ex-prosecutor of the tribunal, came to Paris a few months ago, and she had a press conference openly saying that the French have created a safe haven. Now, the change came about apparently after a recent meeting with President Jacques Chirac and the new prosecutor, Carla Del Ponte, in Paris. And apparently, after Chirac emerged from that meeting, things changed. And at 3:17 in the morning of the night of the arrest, French special forces in black masks stormed the house of the parents of Krajisnik and dragged him out barefoot and in his pajamas. So that is a big change, indeed. That's why there's more hope that we may see more of these arrests.
TARGET: Yeah, I think there are cooler heads, now. Iraq - a lot of different elements here. Hans Blix, the new weapons chief, if they ever get the inspectors back into Baghdad and other parts, came up with an organization plan presented to Security Council members. Blix, next Thursday, is going to go before the council.
```

**YOUR LABEL (F or N):** ______

### Row 69

```
PREV: And Matthew Kroenig, Stanton nuclear security fellow at the Council on Foreign Relations, kind enough to join us here in Studio 3A. Thanks very much for your time.
GUEST: Thank you, Neal.
TARGET: Coming up, Joplin, Missouri, a year after the tornado: what happened, and what's happened since? If you've been in the area, give us a call, 800-989-8255. Or email us: talk@npr.org. Stay with us. I'm Neal Conan. It's the TALK OF THE NATION from NPR News.
```

**YOUR LABEL (F or N):** ______

### Row 70

```
PREV: This week on MORNING EDITION, we're exploring the history behind our political debates. Yesterday, we heard changing explanations for a war. Today, we'll meet a novelist whose research on ancient Rome uncovered a familiar story.
GUEST: (Reading) “What Rome was facing was a threat very different from that posed by a conventional enemy. These pirates were a new type of ruthless foe, with no government to represent them and no treaties to bind them.”
TARGET: Robert Harris is reading from his book, “Imperium,” which is a novel about the Roman Empire. And if you think this language sounds like a description of a modern war, consider this quote that Mr. Harris attributes to a famous Roman general.
```

**YOUR LABEL (F or N):** ______

### Row 71

```
PREV: And let's bring another voice into the conversation. Matthew Kroenig is a senior national security fellow at the Council on Foreign Relations. He joins us here in Studio 3A. Nice to have you with us.
GUEST: It's a pleasure to be here, thanks, Neal.
TARGET: I know your - what signals are you looking for tomorrow? I know you're concerned about another set of delays from Iran.
```

**YOUR LABEL (F or N):** ______

### Row 72

```
PREV: Right.
GUEST: Yes, exactly.
TARGET: All right. We have to move on to another very sticky issue on the agenda this week, which is the observer force in the Middle East. And, James, what's your reaction to the secretary-general's effort on that part?
```

**YOUR LABEL (F or N):** ______

### Row 73

```
PREV: ... news that President Mubarak has appointed a vice president, the first time in 30 years. He is Omar Suleiman, the head of the intelligences services. Also, Ahmad Shafiq, the head of the air force, will become the new - or is the new prime minister. Will either of those appointments have much of an impact? Will they satisfy the public?
GUEST: I don't think so. This is another last-ditch attempt by the Mubarak regime to survive this. But the calls of the protesters have been for the ouster of the Mubarak regime; for Mubarak to get on a plane and join his friend Ben Ali in Saudi Arabia. Now, this was a shrewd...
TARGET: The former president of Tunisia, of course.
```

**YOUR LABEL (F or N):** ______

### Row 74

```
PREV: Ambassador Hof, as a former State Department official, can you reflect on any of this?
GUEST: ... late in the term of President Assad's father, Hafez al-Assad, when there were some very serious and detailed discussions about the contours of a possible peace agreement between Israel and Syria. That process collapsed right around the time of President Hafez al-Assad's death. And when Bashar al-Assad took over as president, it took a while for any kind of relationships to begin to mature. I would sum it up like this: Yeah, I think President Bashar al-Assad was certainly interested in having a cordial, productive relationship with the United States, certainly a relationship without any economic sanctions or any of that business, but was never really willing to do what it would take to have that kind of a relationship.
TARGET: Deb Amos, do you get a sense from your time in Syria that his circle is shrinking? Clearly, the rebels have held more territory recently than they were holding a year ago. How are things changing over the course of this conflict?
```

**YOUR LABEL (F or N):** ______

### Row 75

```
PREV: Well, they seem to have been treated fine. What's the problem?
GUEST: Absolutely.
TARGET: Speaking of human rights, the United Nations was planning a report, the Human Rights.
```

**YOUR LABEL (F or N):** ______

### Row 76

```
PREV: ... a few of those. We have one from Harvey(ph), who writes: Iran has as much right to nuclear arms as anyone else. Rhetoric is silly. We are the only country to have used nuclear weapons during war. When it comes to projecting power, we are not innocent. We need to learn to live with other nations on an equal footing.
GUEST: ... still think that there is a lot to worry about with a nuclear-armed Iran, even if they're not suicidal. After all, the United States wasn't suicidal during the Cold War, but we were willing to risk nuclear war a number of times in crises with the Soviet Union, and we came very close to a nuclear exchange. So I think similarly, a nuclear-armed Iran, you know, on top of all the threats I pointed out to you before of them being more aggressive, further proliferation, and the list goes on, that they would also be willing to risk nuclear in crises with Israel and crises with the United States, and any one of those would have the possibility of escalating.
TARGET: So you see sort of a nuclear domino theory taking place. Suzanne Maloney, can you respond to Alan's point on the presence of a nuclear Iran just setting off essentially a domino effect of other nuclear states being born?
```

**YOUR LABEL (F or N):** ______

### Row 77

```
PREV: A candidate.
GUEST: ...in those elections. So this opens up all kinds of possibilities. I think in theory, that is a very nice transition. Unfortunately, the constitution, over the last couple of years, has been amended at the whim of the ruling party, and tailored to meet their needs in the sense that presidential candidates can't come forward. There are all kinds of restrictions that limit who can become a presidential candidate. And that's why Mohamed ElBaradei, for example, is excluded. So that article of the constitution, Article 76, would also have to be amended in order to have genuinely free and fair elections after 60 days.
TARGET: So who could potentially fill the vacuum? I mean, we know that the only credible opposition in Egypt has been the Muslim Brotherhood. Mubarak, of course, has tried to suppress that movement. You mentioned Mohamed ElBaradei, the former head of the International Atomic Energy Agency. He is trying to raise his profile as a possible opposition leader. What do you imagine a post-Mubarak government could look like?
```

**YOUR LABEL (F or N):** ______

### Row 78

```
PREV: And these numbers don't seem to leave a lot of room for ambiguity. Crime has been going down steadily for three years now. Perceptions trend in the opposite direction. How come?
GUEST: Well, first of all, it's definitely a clear decline. In fact, we can think of this as the great American crime decline. It started actually a little bit earlier, in about the mid-1990s. It went down dramatically, leveled off a little bit around 2001, and it's continued its decline. In fact, at least in terms of the country at large and in many cities, we're looking at crime rates now that are about the level that we saw in the 1950s or early '60s.
TARGET: The good old days.
```

**YOUR LABEL (F or N):** ______

### Row 79

```
PREV: And of course, we're still days away from defense ministers from West Africa, including Nigeria, meeting. I just want to get a final prediction here from you. I mean, it seems, compared to the gloom of last week - I don't know - from an observer point of view, it looks like the UN is going to hold.
GUEST: I totally agree. That's what I was saying. That the wind has somewhat changed towards the UN action in Sierra Leone that everybody feels this is a collective responsibility mission.
TARGET: So the UN may come out looking better, despite the humiliation.
```

**YOUR LABEL (F or N):** ______

### Row 80

```
PREV: We have a question here from Suzanne(ph), who asks: Do any of the guests have insights about Assad will leave Damascus to go to the Latakia region? This region has so far been spared the destruction that other areas have suffered. Ambassador Hof?
GUEST: I think there is probably a pretty good chance that that, ultimately, Assad and his family will move to that region, perhaps as a step toward moving abroad. But clearly, clearly, right now, his top priority is to retain control of Damascus. If he loses Damascus, he's finished, because he is basically of very marginal use to his own supporters once that happens.
TARGET: Thanks for the call.
```

**YOUR LABEL (F or N):** ______

### Row 81

```
PREV: ... North Korea, and with North Korea, we didn't quite have the debate and the discussion and perhaps the option to do something about it militarily ahead of time in the same way that's being discussed now. But in what way are we able to tolerate a nuclear North Korea in a way that would be different from a nuclear Iran?
GUEST: ... And North Korea has only had nuclear weapons for a couple of years. It conducted its first test in 2006. And so we haven't seen the full range of consequences from a nuclear-armed North Korea. North Korea could have nuclear weapons for decades. In fact, there's only been one country historically to voluntarily give up nuclear weapons, so when you're talking about proliferation to Iran or North Korea, you're talking about a threat that the United States is going to have to live with potentially for decades or longer. So we could still have a nuclear exchange with North Korea. So I think looking at the North Korea model gives me reason to be very concerned about proliferation in Iran.
TARGET: We've received some emails from listeners, and I just want to share a few of those. We have one from Harvey(ph), who writes: Iran has as much right to nuclear arms as anyone else. Rhetoric is silly. We are the only country to have used nuclear weapons during war. When it comes to projecting power, we are not innocent. We need to learn to live with other nations on an equal footing.
```

**YOUR LABEL (F or N):** ______

### Row 82

```
PREV: Meanwhile, if that poll is correct, three quarters of us do not believe this. And not only don't believe it, believe exactly the opposite.
GUEST: Yes. It's an interesting paradox. Although when one begins to probe it, it's a little less surprising. And I think there are several reasons. One, most Americans, when they tend to think about crime, tend to relate it to economic conditions, what I think of as sort of a materialist fallacy.
TARGET: Mm-hmm.
```

**YOUR LABEL (F or N):** ______

### Row 83

```
PREV: All right, Eugene Rivers, a Pentecostal minister, community activist and co-founder of the city's 10-point Coalition, and Robert Sampson, professor of social science at Harvard University. I thank you both for joining us. Appreciate it.
GUEST: Thank you.
TARGET: This is NPR News.
```

**YOUR LABEL (F or N):** ______

### Row 84

```
PREV: My understanding is that if it is deployed, there is very little time to respond.
GUEST: There is very little time to respond, and I - you know, I suspect, you know, going back to the initial point, Ari, about why the speech, what President Assad was saying, the chemical element of this weighs in the equation, because on the one hand, you have Assad saying the situation is well in hand. I'm dealing with a handful of foreign terrorists with foreign masters. I'm going to dominate this situation. We're going to win. And on the other hand, he's willing to contemplate the absolutely desperate measure of using chemical munitions against his own people. So there is a basic contradiction there.
TARGET: Recent months have been the deadliest in the nearly two years of fighting, and President Bashar al-Assad's defiant speech Sunday in Damascus confirmed that he has no intention of yielding to calls for his resignation.
```

**YOUR LABEL (F or N):** ______

### Row 85

```
PREV: Business contracts were good to go in.
GUEST: On the other side, the Americans focused on smuggling, which has become a big deal, not just in the Iraq context, but because the oil prices are rising.
TARGET: Afsane Bassir Pour, briefly your take on which way was Annan leaning, and what did he mean?
```

**YOUR LABEL (F or N):** ______

### Row 86

```
PREV: But let me ask you, Samer Shehata, 30 years in power, Mr. Mubarak must have some supporters.
GUEST: ... of whom fled the country yesterday or two days ago on private jets, including the hated Ahmed Ezz, a steel mogul, and also one of the people in charge of the ruling party. So there were some people who were in charge who supporting Mubarak. But the point is that, over the last 25 years or so, the bases of the regime have changed. They have shed workers, they have shed farmers, they have shed civil society, middle-class people as bases of support because of the elimination of subsidies and privatization and so on. And they have taken, instead, large capital as the basis of support, in addition to the military and, of course, the foreign backers, the international community.
TARGET: You're listening to TALK OF THE NATION from NPR News.
```

**YOUR LABEL (F or N):** ______

### Row 87

```
PREV: Joining us in the studio is Samer Shehata, an assistant professor of Arab politics at Georgetown University. Nice to have you with us today.
GUEST: Thank you.
TARGET: You know, I think what's remarkable about this, is if this speech was perhaps made on Friday, it may have changed the intensity of the protest, the intensity of this uprising. But events have moved very quickly since Friday.
```

**YOUR LABEL (F or N):** ______

### Row 88

```
PREV: They buy a lot of Iranian oil.
GUEST: That's right and other commercial relationships, as well. But they also have good reason to maintain good relation with us. And so basically they said they don't want to get in the middle of it. They'll go along with incremental pressure, as long as the rest of the international community is onboard but that they're not going to take tough measures really one way or the other.
TARGET: And Gary Sick, again with some experience in these matters, is Matthew Kroenig right? This is going to take weeks, months, maybe even longer, and therefore you need to have some assurances that Iran is not just playing for time?
```

**YOUR LABEL (F or N):** ______

### Row 89

```
PREV: But in this speech, Bashar al-Assad effectively said: I'm not buying into this plan. I'm not going anywhere.
GUEST: Well, that's exactly right, and - although I don't know if Brahimi has commented on it yet. The secretary-general of the United Nations certainly has, and he has - he's decried the speech because it's quite defiant. It misidentifies the nature of the problem that the Assad regime faces.
TARGET: And so where does that leave us? More blood, more civilian deaths on top of the 60,000 that have already taken place? Or could this speech galvanize the international community to a level that we haven't seen yet?
```

**YOUR LABEL (F or N):** ______

### Row 90

```
PREV: ... in your own country, when it was seen as the leading nation in the world in the 1770s. In 1776, as a matter of fact, in England, there was the publication of the first volume of the famous Edward Gibbon's Decline and Fall of the Roman Empire. Is this something that caused great interest and anxiety for the British then?
GUEST: ... collapse of Pompeii when it was destroyed. This was an object of great interest and fascination to the Victorians, I think because it's one of those perennial stories people go back to just to give themselves a (foreign language spoken) of terror that nature - however sophisticated your civilization, or you think you're well-protected against it - nature has a habit of biting back. And I think that it's the same with the whole concept of the Roman Republic and the Roman Empire. In America now, at the zenith of its power, what a perfect time to start looking over your shoulder and wondering when it's going to be America's turn next, just as it came to the Romans eventually.
TARGET: I was in a meeting the other day when someone said, I was just in New Orleans, and it's the American Pompeii.
```

**YOUR LABEL (F or N):** ______

### Row 91

```
PREV: My understanding is that if it is deployed, there is very little time to respond.
GUEST: There is very little time to respond, and I - you know, I suspect, you know, going back to the initial point, Ari, about why the speech, what President Assad was saying, the chemical element of this weighs in the equation, because on the one hand, you have Assad saying the situation is well in hand. I'm dealing with a handful of foreign terrorists with foreign masters. I'm going to dominate this situation. We're going to win. And on the other hand, he's willing to contemplate the absolutely desperate measure of using chemical munitions against his own people. So there is a basic contradiction there.
TARGET: Although even they seem to have made clear that if Assad uses chemical weapons, all bets are off.
```

**YOUR LABEL (F or N):** ______

### Row 92

```
PREV: And so where does that leave us? More blood, more civilian deaths on top of the 60,000 that have already taken place? Or could this speech galvanize the international community to a level that we haven't seen yet?
GUEST: I suspect, Ari - and I'm sorry to reach this conclusion - but I do suspect it means more blood. It means a protracted process. It means yet more combat on the ground. It means yet more regime attacks on bread lines, on populated areas. So we are going to see the casualty count mounting, I'm afraid.
TARGET: I was reading about these tent cities where people are being frozen and washed away and living in misery.
```

**YOUR LABEL (F or N):** ______

### Row 93

```
PREV: ... has to be the solution - and again, Matthew, I think you're also - you're agreeing that a negotiated solution would be better. But if there had to be a military solution, Suzanne is saying that it would be very temporary, that the Iranians would be able to rebuild and get us back in this position again. What about that?
GUEST: ... almost certain the United States would completely destroy Iran's key nuclear facilities. This would, at a minimum, set Iran's nuclear program back. But, of course, the hope would be that something happens to where Iran ends up permanently without nuclear weapons. And there are examples in the past, for example, Syria bombed - I'm sorry - Israel bombed a nuclear reactor in Syria in 2007, and there are no indications that Syria has rebuilt its nuclear facility since then. So it's possible that Iran could simply give up in the aftermath of a strike. But there's a lot that could happen with that additional time to where we end up in a situation where Iran is permanently without nuclear weapons.
TARGET: But Matthew is making point that...
```

**YOUR LABEL (F or N):** ______

### Row 94

```
PREV: My understanding is that if it is deployed, there is very little time to respond.
GUEST: There is very little time to respond, and I - you know, I suspect, you know, going back to the initial point, Ari, about why the speech, what President Assad was saying, the chemical element of this weighs in the equation, because on the one hand, you have Assad saying the situation is well in hand. I'm dealing with a handful of foreign terrorists with foreign masters. I'm going to dominate this situation. We're going to win. And on the other hand, he's willing to contemplate the absolutely desperate measure of using chemical munitions against his own people. So there is a basic contradiction there.
TARGET: Well, it's interesting that you say that, because I think that is most of their concerns, and it's about daily life. But when there was interest in the international community a few weeks ago, I didn't talk to anybody on the ground who didn't think he would do it. All along, the regime has tested the international community. Is it OK to kill 10? Is it OK to kill 100? Is it OK to kill 5,000 a month? And the answer every time has been yes, it is.
```

**YOUR LABEL (F or N):** ______

### Row 95

```
PREV: That being said, does it run the risk with a protracted delay seeming as if they're countenance in the use of chemical weapons?
GUEST: There are all kinds of risks associated with a protracted delay. It's not clear yet when exactly the administration is going to get to the point where it thinks it has an air-tight case on chemical weapons. No doubt there is also a temptation to allow this potential Geneva peace conference process to drag things out. Already, the conference is pushed back to July. And as of right now, you know, there's really no prospect of substantive negotiations there.
TARGET: Let me ask about something I've read in a number of assessments this week, which suggests that the United States has to be concerned about if it looks like it's setting up a red line and then not doing anything about it in Syria, it sends a message to Iran along the same lines.
```

**YOUR LABEL (F or N):** ______

### Row 96

```
PREV: So you see something really crossing the line in terms of the politicking here - I mean, something that - that has truly gotten extreme in your mind.
GUEST: ... on around it. I'm not sure how many minds are being changed. I think most people's minds were pretty well made up to begin with. There's been a lot of disparaging of experts and the elite, which has been quite disturbing. I mean - and I think a lot of people aren't really qualified, quite frankly, to take the economic view. You feel that the country has fallen into the hands of demagogues, and it feels frightening. I do notice, from sitting here 3000 miles away, slight similarities to the phenomenon of Donald Trump. This is the same harping on about immigration, the same sense that people have been let down by the system, the same turning on the elites.
TARGET: Let me just ask you about the Donald Trump phenomenon that you see a comparison to. I mean, many see people supporting, you know, Donald Trump as having extreme views. I mean, but others say there's a real, legitimate anger there that is driving a movement in the United States, and it seems to be driving movements elsewhere in the world. I mean, rather than sort of dismissing it as demagoguery, I mean, is there something that we should really be grappling with as - as a world today, where this anger's coming from?
```

**YOUR LABEL (F or N):** ______

### Row 97

```
PREV: I mean, if you were them, Matthew, would you negotiate at this point? Is there - would you see an argument to be made internally that we should stop all of this?
GUEST: Well, Iran's primary strategic goals are to continue to exist as a state and to become the most dominant state in the region, and nuclear weapons gives them both of those things. And so nuclear weapons, I think, are seen as very valuable, and the supreme leader right now is not looking for a nonproliferation agreement with the country that is known the Great Satan. That's not what he's looking for.
TARGET: And, Suzanne, the same question to you: do you see indication that the Iranians are perceiving an incentive to back down?
```

**YOUR LABEL (F or N):** ______

### Row 98

```
PREV: He says it's a working assumption.
GUEST: And he said there will always be uncertainty in disarmament.
TARGET: James?
```

**YOUR LABEL (F or N):** ______

### Row 99

```
PREV: The Israelis have offered an apology for that, what they say, the accidental killing of some Egyptian border guards. Is that related to the prisoner swap, the apology?
GUEST: I think there's no question that it's related. The official Egyptian newspaper, Al-Ahram, reported yesterday that the apology was issued an hour after news of the prisoner swap was announced in Israel. So I think Egypt managed to also extract from Israel something that many Egyptians wanted, in fact, demanded, which was an official apology for the killing of the five Egyptian soldiers in Sinai in August.
TARGET: So this is success for what is still officially a transitional regime in Egypt. But it shows some leadership in the region, nonetheless.
```

**YOUR LABEL (F or N):** ______

### Row 100

```
PREV: I know your - what signals are you looking for tomorrow? I know you're concerned about another set of delays from Iran.
GUEST: ... serious consideration of taking military option off the table. So realistically, those kind of negotiations are going to take weeks, maybe months. So I think in Baghdad what we're looking for is something more modest. And so I agree with the previous guest on this. And so my understanding is the U.S.' best outcome is some kind of interim deal, where we get Iran to do three things: ship out stockpiles of low-enriched uranium, stop enriching to 20 percent and shutting down the facility at Qom. And those three things are important because it would buy time, it would make it more difficult for Iran to dash to a nuclear weapons capability in short order if it did those things.
TARGET: And therefore provide more time for talks.
```

**YOUR LABEL (F or N):** ______

### Row 101

```
PREV: ... has to be the solution - and again, Matthew, I think you're also - you're agreeing that a negotiated solution would be better. But if there had to be a military solution, Suzanne is saying that it would be very temporary, that the Iranians would be able to rebuild and get us back in this position again. What about that?
GUEST: ... almost certain the United States would completely destroy Iran's key nuclear facilities. This would, at a minimum, set Iran's nuclear program back. But, of course, the hope would be that something happens to where Iran ends up permanently without nuclear weapons. And there are examples in the past, for example, Syria bombed - I'm sorry - Israel bombed a nuclear reactor in Syria in 2007, and there are no indications that Syria has rebuilt its nuclear facility since then. So it's possible that Iran could simply give up in the aftermath of a strike. But there's a lot that could happen with that additional time to where we end up in a situation where Iran is permanently without nuclear weapons.
TARGET: All right, Jay. Thanks for your call. You're listening TALK OF THE NATION from NPR News. Suzanne Maloney, Jay's point about just the cost of war, just the dollar cost of war being something we can't handle right now, does that figure into your description of why a military option would be less preferable to living with a nuclear Iran?
```

**YOUR LABEL (F or N):** ______

### Row 102

```
PREV: My understanding is that if it is deployed, there is very little time to respond.
GUEST: There is very little time to respond, and I - you know, I suspect, you know, going back to the initial point, Ari, about why the speech, what President Assad was saying, the chemical element of this weighs in the equation, because on the one hand, you have Assad saying the situation is well in hand. I'm dealing with a handful of foreign terrorists with foreign masters. I'm going to dominate this situation. We're going to win. And on the other hand, he's willing to contemplate the absolutely desperate measure of using chemical munitions against his own people. So there is a basic contradiction there.
TARGET: Andrew Tabler, what can you tell us about backdoor contacts with Syria?
```

**YOUR LABEL (F or N):** ______

### Row 103

```
PREV: My understanding is that if it is deployed, there is very little time to respond.
GUEST: There is very little time to respond, and I - you know, I suspect, you know, going back to the initial point, Ari, about why the speech, what President Assad was saying, the chemical element of this weighs in the equation, because on the one hand, you have Assad saying the situation is well in hand. I'm dealing with a handful of foreign terrorists with foreign masters. I'm going to dominate this situation. We're going to win. And on the other hand, he's willing to contemplate the absolutely desperate measure of using chemical munitions against his own people. So there is a basic contradiction there.
TARGET: And we might not know.
```

**YOUR LABEL (F or N):** ______

### Row 104

```
PREV: What does it all mean? Is there like a big pie chart of who's doing what? What's the political implication?
GUEST: Well, you touched, actually, on the heart of the matter, which is these inspectors - will they ever get back into Iraq? Now, the council was counting on Russia, especially, but France and China, also, to persuade Baghdad to accept these inspectors who have not been there since December of '98. Now, this hasn't been done. The Russians are saying, "We're not going to do anything to exert any influence on Baghdad."
TARGET: Did they like the Blix report?
```

**YOUR LABEL (F or N):** ______

### Row 105

```
PREV: I want to ask you, do you think that a strategy of containment could work with Iran?
GUEST: ... If they got nuclear weapons, we could in place a deterrence and containment regime, as she suggests, but, you know, again, this is talking about a massive increase of U.S. political and military commitments in the region. So this would mean signing formal security guarantees with Saudi, other Gulf states and Israel, extending our nuclear umbrella over those countries as we did during the Cold War. And so again, let's call a spade a spade. What we're talking about doing here is fighting a nuclear war on behalf of Saudi Arabia, on behalf of Gulf states, on behalf of Israel. I'm not sure that that's something that the American public is willing to commit to. So it's a dangerous option.
TARGET: Our number is 800-989-8255. Our email address is talk@npr.org. And you can also join the conversation at our website. Go to npr.org, and click on TALK OF THE NATION. Our guests today are Suzanne Maloney, she is a former policy advisor to the U.S. State Department and now a senior fellow at the Brookings Institution; and Matthew Kroenig, Stanton Nuclear Security Fellow at the Council on Foreign Relations and an assistant professor of government at Georgetown University.
```

**YOUR LABEL (F or N):** ______

### Row 106

```
PREV: ... a few of those. We have one from Harvey(ph), who writes: Iran has as much right to nuclear arms as anyone else. Rhetoric is silly. We are the only country to have used nuclear weapons during war. When it comes to projecting power, we are not innocent. We need to learn to live with other nations on an equal footing.
GUEST: ... still think that there is a lot to worry about with a nuclear-armed Iran, even if they're not suicidal. After all, the United States wasn't suicidal during the Cold War, but we were willing to risk nuclear war a number of times in crises with the Soviet Union, and we came very close to a nuclear exchange. So I think similarly, a nuclear-armed Iran, you know, on top of all the threats I pointed out to you before of them being more aggressive, further proliferation, and the list goes on, that they would also be willing to risk nuclear in crises with Israel and crises with the United States, and any one of those would have the possibility of escalating.
TARGET: All right, Dan, thanks very much for your comment. I want to come to Alan(ph) in Phoenix, Arizona. Hi, Alan, you're on TALK OF THE NATION.
```

**YOUR LABEL (F or N):** ______

### Row 107

```
PREV: Well, a lot of the - James?
GUEST: I mean, we're never going to agree on this. I thought Blix - I was very impressed.
TARGET: Well, we only have.
```

**YOUR LABEL (F or N):** ______

### Row 108

```
PREV: It was, of course, this last year that we saw all the demonstrators in Tahrir Square and all over Egypt. What does it mean for the democracy movement that we've followed so closely?
GUEST: Well, it means that the transition to democracy in Egypt is certainly not guaranteed, and the best we can say about it is that it's a mess. It has not been orderly. There has not been a process that has achieved consensus with regard to a constitution, elections and so on. And there are concerns by many that the Muslim Brotherhood is now attempting to exert greater control over the political process, possibly dominating the political process at the expense of the original goals of the revolution.
TARGET: Mohammed Morsi's election this year in June raised some concerns that after the Arab Spring that there would be a way that Islamist governments in the region, that that would make things even more unstable. Do you think that's what we're seeing?
```

**YOUR LABEL (F or N):** ______

### Row 109

```
PREV: One of them, perhaps the Wafd Party, W-A-F-D. This is I guess the oldest opposition party in Egypt.
GUEST: That's right. The Wafd actually didn't participate or didn't call for the demonstrations on January 25th. They later, like the Muslim Brotherhood, after the initial days of protest and the numbers of people who went out onto the street, then lent their support to the protests. But the Kefaya Movement, certainly, kefaya means enough, the enough-to-Mubarak movement, which was established in 2004, was also calling for protests initially on January 25th, and so was the National Association for Change, Mohamed ElBaradei's group.
TARGET: In a piece in today's Times, in fact, you quote some people in the protest saying: We want no parties, we want no leaders, we want Mubarak out.
```

**YOUR LABEL (F or N):** ______

### Row 110

```
PREV: A few weeks ago, there was an acute international fear that Bashar al-Assad was going to use chemical weapons against his people. Ambassador Frederic Hof, is that fear still very acute? Has that threat subsided?
GUEST: The fear is still acute. My understanding is that the weaponry is, in fact, ready to be deployed. So this is something that the international community I think is going to continue to rivet attention on.
TARGET: My understanding is that if it is deployed, there is very little time to respond.
```

**YOUR LABEL (F or N):** ______

### Row 111

```
PREV: Robert Harris, you're writing a fictional account of the Roman Empire, but based on real events. Why, when you're looking at events from 2,000 years ago, draw such an exact parallel with what's happening today?
GUEST: ... the Port. The flames may well have been visible in Rome itself. And this sent a shockwave through Rome, because if pirates could strike that close to the imperial capital, nowhere was safe. And in this panicky atmosphere - an atmosphere of panic, I might say, which was deliberately whipped up by ambitious politicians - the Roman people took a series of fatal steps, surrendering some of their liberties and some of their control over their government. And in doing so, they sewed the seeds of the destruction of their own democracy. And the more I looked at that event, the more it seemed familiar to me and the parallel with 9/11 - and in particular the response to it.
TARGET: Were there very similar debates about civil liberties? About how far to go? About how much people had to change in order to battle this threat?
```

**YOUR LABEL (F or N):** ______

### Row 112

```
PREV: Go ahead.
GUEST: ... may have to do more with how people are perceiving the change in our country rather than crime per se. In other words, what the Gallup poll and other things do show is that our perceptions about crime track a more abstract notion having to do with satisfaction with our country. That makes a certain amount of a sense. If people think the country is going to hell in a hand basket, then they tend to expand from that to a bunch of other bad things. So we know from lots of different polls that there's a lot of dissatisfaction right now with government, there's concern with the economy, people know it's bad. They extrapolate, in other words, from that.
TARGET: But even...
```

**YOUR LABEL (F or N):** ______

### Row 113

```
PREV: ... with you. We heard from Phillip Martin the idea, if you will, of the changing of America, to a great degree the browning of America, being just one--and I underline just one--of the problems that we are seeing in terms of the escalation of violent crime, particularly murder in this country. There are so many contributing factors, though, aren't there?
GUEST: ... standing of the city. That said, there's certainly an increase and certainly a problem. I would be hesitant to blame it all on immigration. In fact, in terms of national statistics, immigration seems to be, if anything, related to lower rates of crime and violence. And some of our most diverse cities with exploding immigrant populations--Los Angeles, Chicago metropolitan area and others--again are experiencing decreases. So it is a complicated picture and one can't point to any single factor like that. And in fact I think the immigration finding is something that needs to be re-enforced because it can lead to stereotypes that suggest that specific race or ethnic groups are somehow inherently more likely to be involved in violence.
TARGET: Reverend Rivers, let me turn our attention to you and ask you. You have been involved in this fight for quite some time. I'm curious what you see as the most pervasive issue in terms of dealing with trying to eradicate the violent crime and, quite frankly, the disproportionate violent crime that affects African-American men in this country.
```

**YOUR LABEL (F or N):** ______

### Row 114

```
PREV: Well, beyond religious issues, Samer Shehata, how do basic economic issues factor into the crisis we're seeing now in Egypt?
GUEST: Well, I think there's no question that that was a large component of it. The economy has been spiraling downwards with increasing unemployment, fuel shortages, bread shortages, labor strikes and an inability to secure an IMF loan, increasing borrowing, deteriorating exchange rate. And so this certainly contributed to outrage at Mr. Morsi and the Muslim Brotherhood. Many of his promises were unmet.
TARGET: So what about the United States' role in all of this? Samer Shehata, would you say we're in kind of an awkward spot right about now? After all, it was just two months ago that Secretary of State John Kerry approved $1.3 billion in annual U.S. military aid to Egypt. So now with the ousting of Mr. Morsi, many are questioning whether the United States should continue that aid. What do you think?
```

**YOUR LABEL (F or N):** ______

### Row 115

```
PREV: It's fair to say, Matt Kroenig, the United States doesn't quite trust Iran, either.
GUEST: There's a lot of mistrust on both sides. And I think I would agree with the caller that that's a good way forward. In fact, that's something that we've tried in the past, but Iran has been unwilling to accept those fuel assurances from outside. Iran's explanation is that it wants the ability to produce fuel itself for energy security purposes. But I think many people, including myself, suspect that it's - Iran wants the nuclear weapons capability that comes with the ability to produce fuel indigenously.
TARGET: Mike Shuster, at NPR West. Our thanks to Gary Sick, who joined us from his office at Columbia University in New York. Thanks, Gary.
```

**YOUR LABEL (F or N):** ______

### Row 116

```
PREV: It's a question I put to Samer Shehata who teaches Arab politics at Georgetown University.
GUEST: ... look like a political spectrum that includes socialist ideas, that includes liberal ideas, certainly capitalist interests would be represented. Interests of business, labor, for the first time in a very long time, I think, would be represented. And there are millions of Egyptian workers who have been very active over the last three or four years. And then, of course, there would be not one but a range of, I think, Islamist perspectives, including most notably the Muslim Brotherhood, not as a dominating force, but certainly there on the political scene. And there probably will be some elements, some of the cleaner elements that were previously associated with the old ruling party, where the regime in one capacity or another.
TARGET: Samer, when we hear about building a new democracy, rebuilding a democracy in Egypt, we're not necessarily talking about a liberal democracy like the one that, you know, we have here or in Western Europe or are we?
```

**YOUR LABEL (F or N):** ______

### Row 117

```
PREV: Robert Sampson, thanks very much for your time. We appreciate it.
GUEST: Thank you.
TARGET: Robert Sampson of the Department of Sociology and professor of social sciences at Harvard, with us today from a studio there in Cambridge.
```

**YOUR LABEL (F or N):** ______

### Row 118

```
PREV: We have a question here from Suzanne(ph), who asks: Do any of the guests have insights about Assad will leave Damascus to go to the Latakia region? This region has so far been spared the destruction that other areas have suffered. Ambassador Hof?
GUEST: I think there is probably a pretty good chance that that, ultimately, Assad and his family will move to that region, perhaps as a step toward moving abroad. But clearly, clearly, right now, his top priority is to retain control of Damascus. If he loses Damascus, he's finished, because he is basically of very marginal use to his own supporters once that happens.
TARGET: It comes from the outside, and that's why things are so tough in the north. There's hardly any bread. Yes, there are kids going to school in Damascus and Aleppo, but mostly in the government-controlled areas. The kids are going to school in the refugee camps run by parents and volunteer teachers. Up until now, government salaries are still being paid. However, in the past couple of months, somebody just told - weeks, somebody told me this from Aleppo, you now have to show up at a government office to pick up your paycheck.
```

**YOUR LABEL (F or N):** ______

### Row 119

```
PREV: Ambassador Hof, as a former State Department official, can you reflect on any of this?
GUEST: ... late in the term of President Assad's father, Hafez al-Assad, when there were some very serious and detailed discussions about the contours of a possible peace agreement between Israel and Syria. That process collapsed right around the time of President Hafez al-Assad's death. And when Bashar al-Assad took over as president, it took a while for any kind of relationships to begin to mature. I would sum it up like this: Yeah, I think President Bashar al-Assad was certainly interested in having a cordial, productive relationship with the United States, certainly a relationship without any economic sanctions or any of that business, but was never really willing to do what it would take to have that kind of a relationship.
TARGET: Sure.
```

**YOUR LABEL (F or N):** ______

### Row 120

```
PREV: We have to end it there. But thanks very much to Afsane Bassir Pour of Le Monde and...
GUEST: Thank you.
TARGET: Glitter with a purpose. Movie star Sharon Stone acts on her basic instinct to save lives. Stone helped the American Foundation for AIDS Research sound an alarm over the next flash point for AIDS. After ravaging sub-Saharan Africa, many scientist believe South and Southeast Asia could be the next trouble spots of the deadly disease. As the United Nations marked World AIDS Day Friday, it had some mixed statistics to consider - 36.1 million men, women and children worldwide are infected. That is a staggering jump over what experts predicted a decade ago. But there are signs of hope in Africa, where cases of HIV AIDS appear to be stabilizing, thanks in part to education efforts. We leave you with ...
```

**YOUR LABEL (F or N):** ______


---

## Provenance

- Sampling seed: **61**. Rebuild this exact sheet with
  `uv run python experiments/h6_audit_sample.py`.
- Rows: **120**, drawn from **469** model classifications over
  **6** subjects.
- Classifier rubric hash (frozen): `053b96cba42ebf03d966db3c22fce2acde3a685d5b4cca9badd556ee248a24da`
- Classifier records: `results/stage2_pilot/records/classify.jsonl`
- Answer key (do not open until finished):
  `results/stage2_openended/h6_audit_key.json`
