# H6 classifier audit sheet -- part 2 (confirmatory subjects)

**What this is.** A machine read 60 interviewer turns and sorted each one into
one of two boxes. Your job is to sort the same 60 turns yourself, without
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

These 60 rows come from **30 different people**, drawn from a pool of
5268 machine labels over 88 study subjects. The plan asks
for at least 60 rows across at least 10 people, so this sheet clears both. None
of these rows appeared on the first sheet, and none of these people were used
in development.

---

### Row 1

```
PREV: Right.
GUEST: Yeah. It does seem like a little bit of a twist, doesn't it? But the Trump administration says that this is something that has to be controlled by the federal government. And once again, it's not the only time that the Justice Department has gone after California for taking it one step too far from policies that the Trump administration has enacted. That's why you've seen cases on things like immigration and carbon emissions and so forth.
TARGET: So what does this mean? I mean, in the interim, does the state law hold? Can it keep doing what it wants to? And what are the national implications for this suit?
```

**YOUR LABEL (F or N):** ______

### Row 2

```
PREV: ... a piece of history yesterday. In defeating Andy Murray in the men's finals, he became the first player since Rod Laver almost 50 years ago - got to hold all four major men's grand slam tennis titles at once. We've got Courtney Nguyen on the line from Paris. She's senior writer with WTA Insider there. And thanks for joining us.
GUEST: No problem.
TARGET: So an historic win for Djokovic. Was it as convincing to watch this all play out on the court?
```

**YOUR LABEL (F or N):** ______

### Row 3

```
PREV: So Landrieu's loss really marks the end of an era for Democrats in the Deep South. Can you give us the historical context there?
GUEST: So Democrats had largely controlled the South, so if we go back as far as Reconstruction, Democrats had really dominated the South. And so we can look at classic political science work that talks about the South is a one-party Democratic region. And now we've just seen a shift from it being a one-party Democratic region to it being a one-party Republican region.
TARGET: So Dem. Mary Landrieu had bucked the political trend against Democrats in the South for 18 years. What kept her from extending her streak this year?
```

**YOUR LABEL (F or N):** ______

### Row 4

```
PREV: So let's talk about esports, the business of esports. It's been described as the next big thing. How big is the sport right now? How big do you think it could get?
GUEST: The sport right now is not very big, but the potential is huge. And one of the reasons there's such a big potential is that the typical esports viewer and esports player are young males. Those are people that don't watch television. They've never watched television. We talk about cord-cutters in the business. These are cord-nevers. And so advertisers are desperate to try to reach them because they can't reach them anywhere else. So you have companies like Turner Sports, the Big Agency, WME-IMG - they see that advertisers want to reach this group, so they're all trying to get into that group to sort of prove that advertisers should go with them in order to build up the business.
TARGET: Where is the money coming from, though? And sort of where is it going? Where are they investing the money in?
```

**YOUR LABEL (F or N):** ______

### Row 5

```
PREV: Carlos Gutierrez is secretary of Commerce. Mr. Secretary, thank you for joining us on DAY TO DAY.
GUEST: Thank you very much, sir.
TARGET: This is DAY TO DAY from NPR News, and there's more of it just ahead.
```

**YOUR LABEL (F or N):** ______

### Row 6

```
PREV: Do you think anybody will get to Osama bin Laden?
GUEST: I'm convinced that one, he is alive; and, two, that we will eventually get him. A story I filed from there says that he's in Peshawar now, the capital of the North West Frontier province. That information came from a very important tribal leader that I've known for a long time, because I've been in and out of the area for the last 35 years. And he says that he's been -- Osama bin Laden has been inside Peshawar, a city of 3.5 million, since December 9.
TARGET: Why December 9? What was pivotal about that day?
```

**YOUR LABEL (F or N):** ______

### Row 7

```
PREV: And now, my producer tells me that you are - when you return, you're looking into going into possibly journalism. Is that true?
GUEST: ... from this experience and interview a lot of my fellow soldiers and officers and found that I really enjoy collecting those interviews and collecting everyone's thoughts for pieces and putting them down into writing, and so I'd love to be able to continue that. And I think it's a really interesting time in journalism. It's a tough time right now because we're sort of moving from the idea of print journalism and subscriptions into a lot of online readership. But from what I've read, readership online and viewership online is really skyrocketing. So now, you can get those stories out to a much larger audience, which I think will be a great and beneficial aspect in the next couple decades.
TARGET: Yeah. Is there any area you want to focus on when you get back? Any particular subject matter?
```

**YOUR LABEL (F or N):** ______

### Row 8

```
PREV: Minister Ursula Von Der Leyen, thank you so much for joining us today.
GUEST: All right. You're welcome.
TARGET: And when we come back, is the UK'S prime minister in waiting? The smart money today is on Labour Leader Jeremy Corbyn, and he joins me from his party's conference next.
```

**YOUR LABEL (F or N):** ______

### Row 9

```
PREV: Now, back in July, there were millions of Egyptians that really welcomed the ouster of Mohamed Morsi, and you heard a lot of assurances that, well, you know, we will get back to a democracy. What is their reaction now?
GUEST: ... against the government. We've seen opposition to the government's policies spread amongst a small group of people who we've considered sort of anti-government activists over the last three years. And we've seen a lot of non-Islamist activists imprisoned in the last couple of weeks. And so that's new. You do hear a lot of private expressions of concern about the direction of country. The continued struggles of the economy, you know, the fact that for most people things do not seem to be getting better. And you also hear a concern about the idea that we're entering a new military era. People seem to realize that that might represent a real step backwards for the country after all this turmoil.
TARGET: Is there worry also that the Muslim Brotherhood supporters might now be more likely to turn to extremism?
```

**YOUR LABEL (F or N):** ______

### Row 10

```
PREV: All the violence has Syrians fleeing to safer areas inside the country, or across the border. And one of the groups helping them is the United Nations World Food Program.
GUEST: This month, actually, we plan to give food to 2.5 million people inside Syria. This is, by the way, four times the population of Washington, D.C.
TARGET: That's Muhannad Hadi, the World Food Program's emergency coordinator for Syria. He is in Washington, meeting with members of Congress, and he dropped by our studios. Hadi has been working in Syria since before the conflict began, and he says it is becoming increasingly difficult to get food to those in need.
```

**YOUR LABEL (F or N):** ______

### Row 11

```
PREV: George Joffe, thanks as always for your time.
GUEST: You're welcome.
TARGET: Wesley Clark, retired Army general who wrote an op-ed in the Washington Post that raised questions about the wisdom of an American-led military intervention in Iraq, even a no-fly zone.
```

**YOUR LABEL (F or N):** ______

### Row 12

```
PREV: So you think things are better now than they were last time you were there, in 2006?
GUEST: There's not even a comparison. We were here when the Golden Mosque was bombed at the end of February in 2006, and it started the sectarian war, really, that raged for about a year and a half. Whereas every other patrol we seemed to find a dead body in the streets from one sectarian conflict or another last tour, this tour, the people are starting to realize that sectarian violence isn't going to solve anything.
TARGET: Now, our listeners have been writing to you. We have a special web feature where you take questions from them and answer them. What kinds of questions are you getting?
```

**YOUR LABEL (F or N):** ______

### Row 13

```
PREV: What is the reward, now, Beth?
GUEST: Well, now, it's $1 million for her safe return, then, $100,000 for her whereabouts.
TARGET: Do you chalk it up to the limited experience of Aruban police?
```

**YOUR LABEL (F or N):** ______

### Row 14

```
PREV: Some have treated Herman Cain first as a marginal candidate and then with some contempt. And I'm just quoting here from - this is a piece in Politico. This is the magazine that originally reported the allegations about sexual harassment, but this is their chief political columnist Roger Simon.
GUEST: ... presumed frontrunner in the Republican field is not the overwhelming favorite son of Republicans and coupled with the fact that you have a Tea Party revolt, where you have this war between people who want to get back to conservative first principles versus the establishment, that opened up a lot of opportunities for Herman Cain to gain the traction that he has. Ultimately at the end of the day, it's those weaknesses, the lack of familiarity with foreign policy, the lack of familiarity with domestic policy beyond his 9-9-9 plan on issues of taxation are probably what would be his undoing and what would actually be his Achilles' heel not just in the primary but also in a general election.
TARGET: We're talking with Andra Gillespie, professor of political science at Emory University. We want to hear your thoughts, too. How has the rise of Herman Cain changed the discussion about race and politics? 800-989-8255. Email talk@npr.org. David's(ph) on the line, David with us from Keane in New Hampshire.
```

**YOUR LABEL (F or N):** ______

### Row 15

```
PREV: Take the rest of the world as part of our conversation. There are quite a few female leaders internationally. But what has kept America back?
GUEST: ... we have a different system than a lot of the countries that have elected women -parliamentary systems versus our system where the president is elected directly by the voters. And I think that makes - that changes it. And I think a lot of these other countries also have quotas when they run slates as candidates in these parliamentary systems. There are a certain number of women that are required to be on the ballot. And as we all know in this country, if you say the Q word, people run fleeing. And so, I think that if the party has made a real commitment to electing women to office, I think we would have more women in elected office.
TARGET: Here's another point. We've talked about external obstacles and male dominance in the political arena. How do you address the issue of self-perception of women and those self-perceptions that you think perhaps women need to overcome for themselves to increase their visibility in the political arena?
```

**YOUR LABEL (F or N):** ______

### Row 16

```
PREV: ... heard from Chuck Todd, the Mark Foley -Congressman Mark Foley - scandal seems to have had some impact. Do voters make any distinction when it comes to the Senate, or what do you get a sense is driving so many voters in the polls, at least, away from, well, even some Republican incumbents who seemed pretty safe earlier this year.
GUEST: You know, I think the Foley scandal per se has not had a direct impact on Senate races. But if you take Mark Foley and continued bad news in Iraq and Bob Woodward's book, State of Denial, which has been quite critical of the administration, and the national security estimates - intelligence estimates - because they were all - all these things happened around the same time. It's almost like it just handed every Republican candidate 20 more pounds of wet sand to carry around.
TARGET: You mean, if you've been standing by the president on Iraq all this time and being a good soldier in the GOP, suddenly it's not such an asset right now.
```

**YOUR LABEL (F or N):** ______

### Row 17

```
PREV: And where would you suggest a venue?
GUEST: I think that there are multiple venues. There are advocacy groups scattered throughout the United States, and I think speaking to those groups is important - as scientists, bringing information to the conversation. I think that shows like these are another venue. I think as scientists, we haven't even began to explore the wonderful, you know, the wonderful world of Tweeter(ph), of tweeting and things like that. But there are - we're not very good about communicating the information. We do it in dry journal format when sometimes a picture will suffice and be much more effective at communicating an idea.
TARGET: Well, I want to thank you all for taking time to join us, and we'll be watching to see how well you are able to communicate those ideas, especially if Congress hold hearings and has invited you folks to come up there. Maybe you can tell them what - instead of them talking to you, what you think about science.
```

**YOUR LABEL (F or N):** ______

### Row 18

```
PREV: Take a listen to what happened at the press conference today.
GUEST: He found a way to be a free man due to his fame. And it is now our opportunity to hopefully take that fame from him, in the form of his right to publicity, his name and likeness, probably the one thing that is important to him, and that`s himself. Hopefully the court will see our right to take that from him, and hopefully, frankly, it will cause him some discomfort and pain.
TARGET: Describing his sex life, nobody cares, but when it comes to entourage of little girls, I care. With us is a special guest, Gary Harris, the Karr family attorney. His theory is that John Mark Karr is no threat. But, sir, I`m reading from court documents, from the first wife, a minor, states she`s fearful for her life and safety. That`s a document filed in court. And the second wife who says her husband, John Mark Karr is a threat to children. Your response?
```

**YOUR LABEL (F or N):** ______

### Row 19

```
PREV: I saw one pair of numbers was about 2 to 1 in the '60s versus the '30s, fair or unfair.
GUEST: Exactly. And we see this across many income categories. There's a big partisan gap on these attitudes, but there's an important other element to this in terms of opportunity. We asked, in the same survey about a month ago, can most people get ahead if they're willing to work hard? And you get about 64 percent saying, yes, they can still. And that number dipped a little bit during the recession, but has come back.
TARGET: You said that there's a big partisan divide here. Are Democrats more likely to say the deck is stacked and Republicans more likely to say it's fair?
```

**YOUR LABEL (F or N):** ______

### Row 20

```
PREV: And please tell us about these two candidates.
GUEST: Well, the Republican candidate who's running is Debbie Lesko. She's a longtime state legislator - quite conservative. She is the Arizona coordinator for the American Legislative Exchange Council, so that'll give you sort of a feel for her points of view. Her Democratic opponent, who, by the way, is the first time that Democrats have run an opponent in this district since 2002 - is a woman named Hiral Tipirneni. She is of Indian descent, came here with her parents when she was, oh, I think, under 5 years old, grew up and became an emergency room doctor.
TARGET: And based on what you've seen so far in the campaign, does Ms. Lesko cite President Trump as any kind of inspiration or example? What kind of relationship does Ms. Tipirneni seem to have with the national Democrats?
```

**YOUR LABEL (F or N):** ______

### Row 21

```
PREV: So a few extreme comments, they're painting the whole...
GUEST: It helps them all. They all can jump on it. The Pennsylvania candidate started using it in his race, quoting the Delaware candidate, you know. And it's an easy thing to throw in when you're down in the numbers.
TARGET: And that's a term that no one will use in their campaign ad.
```

**YOUR LABEL (F or N):** ______

### Row 22

```
PREV: Did the government simply fail to respond?
GUEST: I think a lot of analysts and a lot of folks in Kunduz are saying that, that the government failed to respond. Four, five months ago, they came very close to capturing the city. They took some of the suburbs of the city. And the government barely defended it, and it relied on militias - on very controversial militias to defend the city. So if they came so close to a major city for the first time in 14 years - a few months ago - why didn't the government send reinforcements? Why didn't the government launch clearance operations to push back the Taliban from the surrounding districts that were choking the city? That's where the questions are.
TARGET: Is there any way to know if perhaps the population of that city, or some large part of the population, sympathized with the Taliban side?
```

**YOUR LABEL (F or N):** ______

### Row 23

```
PREV: Sounds pretty good.
GUEST: Yeah, it's doing well. It's what Sean McManus, the president of CBS News and Sports, said is a little pocket of good news amidst this big recession that's really just killing the advertising market.
TARGET: Now, considering all the troubles GM's had since last year's tournament, I don't think anyone expected them to be here at all.
```

**YOUR LABEL (F or N):** ______

### Row 24

```
PREV: In much of the world, the atomic bombs dropped on Hiroshima and then on Nagasaki are not just regarded as not a good thing to have been done. Many people regard this as mass murder. I mean, do the Japanese regard what we did to them as criminal, by and large?
GUEST: ... was a criminal act. It was knowing act of violence that clearly had only one outcome. But I think there's also, in Japan, an increasing willingness to discuss the firebombings of Tokyo. Many more Japanese died in March of 1945 in firebombing raids of Tokyo and other urban settings. The fact that World War II was a terrible war with tremendous civilian casualties is a well-known historical fact. And I think the question now is whether or not we can discuss that reality and discuss it in a way that helps us effectively educate our populations - not just American and Japanese, but Chinese, European, Latin American and other global populations about the terrible damage of this kind of weaponry.
TARGET: Sheila Smith, senior fellow for Japan studies at the Council on Foreign Relations. Thanks for talking with us.
```

**YOUR LABEL (F or N):** ______

### Row 25

```
PREV: So Windows 8, little bit of a catch-up. How innovative is it, though?
GUEST: Well, it is innovative. But what Microsoft is doing - it's sort of a Hail Mary pass, in that what they're trying to do is create a completely new interface for Windows that is more at home in a world of tablets and touch screens; while at the same time, trying to not shock Windows users, and to maintain compatibility with the huge universe of software that's already been written for previous versions of Windows.
TARGET: So let me get this straight: This new user interface, on the new Windows 8, is a - kind of combination of things?
```

**YOUR LABEL (F or N):** ______

### Row 26

```
PREV: Welcome to the program.
GUEST: Thanks for having me, Steve.
TARGET: I have to just say this is an incredible throwback. The city was captured from the Taliban 14 years ago. What happened?
```

**YOUR LABEL (F or N):** ______

### Row 27

```
PREV: So with all this tough rhetoric from President Trump, from Kim Jong Un, how do we get to the de-escalation that you're talking about?
GUEST: I think the key is you have both leaders - and the president has put a marker down. The president has made it clear we are not a paper tiger. He's made it very, very clear. It's coming from the top. I think North Korea - and North Korea knows this. It goes back to the first Gulf War in 1991. Those advisers to Kim Jong Un know what we did to Saddam Hussein in 1991 with the first Gulf War when they went into Kuwait. They saw U.S. capabilities. Well, our capabilities are much greater right now. So there's no question they know what our capabilities are. And North Korea is not suicidal.
TARGET: What role will China play? And what does the U.S. have to do to encourage China to play that role?
```

**YOUR LABEL (F or N):** ______

### Row 28

```
PREV: Debbie, in a year when there was a solid Democratic sweep, would you have expected broader gains among women? Most of the women who were running were Democrats.
GUEST: Well, what we did see was a story of party here, even in the women's races. While we do have 10 brand-new women who've been elected to the House, eight of those women were Democrats, and we saw no losses among the Democratic incumbent women, but we in fact did lose four Republican women from the House, and there's still some of these undecided races that involve Republican. So there's the potential to lose even more. So it's a good news story for Democratic and a not so good news story for the Republican women.
TARGET: In past years, some elections have been considered, or at least one has been considered the year of the woman. You wouldn't consider that the case this year?
```

**YOUR LABEL (F or N):** ______

### Row 29

```
PREV: ... effect do they think President Trump has had on the country. It's interesting that both of you are now in academic settings where, presumably, you get to think a little bit about this - a little bit more deeply than you did when you were actually running from issue to issue every day. So, Mary Kate, I'll start with you.
GUEST: You know, I think - that's a tough question. In a lot of ways, he has really polarized our country. The communications in terms of Twitter and the insulting and the - I don't know what you call that - the volatility has really been remarkable, and I think very damaging to our country. On the other hand, some of the legislative things he's been able to accomplish and some of the stuff going on below the surface - the deregulation, the things that are going on with the economy - are in sort of the positive category. So it's a mixed bag, and I hope it gets better.
TARGET: That's - we're going to have to cut you off there, Fred. More - I hope we'll talk again soon. That's Fred McClure. He's a former director of legislative affairs. He advised both Presidents Reagan and President George H.W. Bush. Mary Kate Cary was with us - also a former speechwriter for President George H.W. Bush - and Sarah Westwood, White House correspondent for the Washington Examiner. Thank you all so much for speaking with us.
```

**YOUR LABEL (F or N):** ______

### Row 30

```
PREV: ... refused because of legal questions raised by the command's lawyers. (on camera): U.S. officials say that are frustrated that they missed Mullah Omar on that day. Permission was later granted to fire on the convoy, but by that time, the Taliban leader was in a safe location. They are determined to get another shot at it. David Ensor, CNN, Washington.
GUEST: My pleasure, thank you.
TARGET: Asthmatics and those with respiratory problems are at greater risk for health damage than the average New Yorker says Dr. Regina Santella.
```

**YOUR LABEL (F or N):** ______

### Row 31

```
PREV: When you look at technology -- we were flipping through the paper earlier: There's a full-page ad by one of the box makers, you know, essentially selling you a computer and a free printer for $699...
GUEST: Right.
TARGET: ... as you look at the box makers and the tech group as a whole, are you attracted to them? Are you going to wait for them? Are they going to be the ones that lead us out of this time right now, or do you wait and sort of let them pick up a little bit?
```

**YOUR LABEL (F or N):** ______

### Row 32

```
PREV: And so how was he killed?
GUEST: He was coming back from an event in Latifiya to his home in Baghdad when they were stopped at a checkpoint by men in military uniform. It was a convoy of about nine people. They were kidnapped and their bodies were found in a Shia district in the north of Baghdad.
TARGET: And his son was with him, right? He was also killed.
```

**YOUR LABEL (F or N):** ______

### Row 33

```
PREV: Jennifer Duffy?
GUEST: Now only is about Iraq, but as mid-term elections tend to be, this is also a referendum on President Bush and his policies on Iraq, on national security, on the economy. You know, this is what mid-term elections are about. They are referendums on the party in power.
TARGET: Well, thanks to both of you for talking politics with us today. Jennifer Duffy of The Cook Political Report and Chuck Todd of the Hotline. Thanks.
```

**YOUR LABEL (F or N):** ______

### Row 34

```
PREV: Yes. Beth and Jug, we thank you again for being with us, our hearts go out to you, we hope for nothing but the best news, the best news, of course, being that she's alive.
GUEST: Thank you so much, Larry and Susan.
TARGET: Being described as very cordial. The people who have been on the ground here over the past couple months working hand in hand with the people -- the Aruban investigators, it's been a very good relationship. Naturally, privately, there have been frustrations expressed about the inability on the part of the FBI to play a larger role, but of course they're invited guests here. And they've got to play by the rules. But certainly things are changing a bit as we previously described, with more of the evidence and investigative materials being shared with the FBI by the Aruban authorities after the head of the Miami FBI office came down and met with law enforcement officials and with the prime ...
```

**YOUR LABEL (F or N):** ______

### Row 35

```
PREV: ... amount to the two percent of GDP on your military spending. So the president will continue to criticize you for that. I guess my question is, what do you make of Senator Ambassador Kay Bailey Hutchison's description of President Trump's loud complaint as a strategy to get you all together and to make NATO stronger by having it's militaries stronger?
GUEST: ... defense budget on your defense budget nationally without contributing anything to NATO for example. Therefore I think, and we agreed on that in the alliance. It's worse to look at two other metrics, but our capabilities given to NATO and contributions to NATO missions. And I think (inaudible) is that Germany is the second largest troop contributor to NATO mission overall. We're just - we're just talking about the NATO command structure. Germany is leading the joined support in enabling command the new (inaudible). In order, we are the second largest net payer to NATO. So these are numbers that show that NATO is benefiting from the German contribution, as we all try to contribute as good as possible to
TARGET: OK, so let me take the first bit first. President Trump saying I don't know what we the United States get out of essentially protecting you Germany, you Europe. Could you answer that first, what's in it for the U.S.?
```

**YOUR LABEL (F or N):** ______

### Row 36

```
PREV: And let us begin with the men. Novak Djokovic dispatched his old nemesis Rafael Nadal in the quarterfinals and looked to be cruising to his first ever French Open victory, and then what happened?
GUEST: And then he ran into an absolutely red-hot Stan Wawrinka, a player who on any given day can beat any given player. He's just not always a consistent guy, so we don't really write him into these final matches or think that he's going to make a big run. But Stan Wawrinka played one of the best matches he's ever played in his career to upend Novak Djokovic in what felt like a to-be coronation ceremony before the serve, who was looking to complete his career slam here at the French Open.
TARGET: And tell us more about him. I mean, he's not young - 30 years old - for a tennis player, but this is his second major in the last year and a half. What's he done to up his game?
```

**YOUR LABEL (F or N):** ______

### Row 37

```
PREV: But if you have a situation where the U.S. is already evaluating Africa from a distance, wouldn't it make more sense to have the United States evaluating it up close with - is that an argument that has any, you know - does it wash with you?
GUEST: Farai, what we recognize is that this Bush administration is really focused on its quest for oil at all cost. And we recognize the high strategic value of Africa's resources, particularly oil, but also, as you were talking about in the previous segment, uranium. There are tremendous strategic reserves in the African continent. And as the Bush administration looks to Africa for more of its addiction to oil and these other vital resources, it is looking also to expand its military presence. It is not in the interest of Africa. It is actually not even in the interest of the U.S. to further - to put additional military personnel in harm's way for the quest of oil.
TARGET: Now, the Liberian president, Ellen Johnson Sirleaf, has invited AFRICOM to set up headquarters in her country, which also happens to be your country of origin. But many others question AFRICOM's intent. The senior Pentagon official, Ryan Henry, says the new command is not about increasing military presence in Africa but rather restructuring what already exists.
```

**YOUR LABEL (F or N):** ______

### Row 38

```
PREV: The beneficiaries included Iran's U.S.-backed king, Shah Reza Pahlavi. To be sure, many countries received what Iran did - their own small reactors, their own dollops of fuel.
GUEST: It was only in Iran, as a result of the oil boom of the 1970s, that the nuclear program morphed into a full-fledged civilian nuclear program.
TARGET: Oh, because the Iranians had the money to exploit the knowledge they were given?
```

**YOUR LABEL (F or N):** ______

### Row 39

```
PREV: Have you done any polling on how the recent scandals in Washington have affected voters? For example, the Congressional page scandal?
GUEST: We have not, but we were in the field when the Foley scandal really erupted, and so we cut our field period in half and divided half before the Foley resignation, half after. We showed no difference in the Congressional horserace, the generic ballot as it's called. Democrats were pretty far ahead by 13 points before Foley resigned, and they were ahead just as far after Foley's resignation. So it doesn't seem to have had an impact on the Congressional race itself.
TARGET: You have another poll out that shows that Democratic voters are more motivated - a lot more motivated - than Republican voters this election season. Tell us about that.
```

**YOUR LABEL (F or N):** ______

### Row 40

```
PREV: So what would be the point, given that the majority of the imports come from - what? - like, Brazil, Canada, Germany?
GUEST: Exactly. It really is designed to protect U.S. steel and U.S. aluminum. That's the theory. What we have learned over the years is that protectionism doesn't protect. Protectionism actually harms. And this is so much bigger than steel and aluminum because what we're doing is challenging the world trade system that we played an important part in bringing together. So that's a problem.
TARGET: Well, the president seems to agree with that. I mean, he said - he tweeted on Friday morning, for example. The president tweeted that, quote, "trade wars are good and easy to win." What is your response to that?
```

**YOUR LABEL (F or N):** ______

### Row 41

```
PREV: Arizona has only sent 11 senators to Washington in the state's history. Those senators have generally been mainstream conservative, white men. The 2018 race is much more dynamic. Headlines have described the Arizona race as a free-for-all and bedlam. Here to talk with us about it is Arizona Republic political columnist Laurie Roberts. Welcome.
GUEST: Thank you for having me.
TARGET: So Senator Jeff Flake is retiring in 2018. And this is a delicate question, but we need to acknowledge that Senator John McCain is being treated for brain cancer and may retire before the 2018 election. Do people in Arizona see this as a race for one seat or possibly two?
```

**YOUR LABEL (F or N):** ______

### Row 42

```
PREV: Do you have any sense, Michelle, of what sort of stigma these women and girls may face if they do go back to their home communities?
GUEST: I think there's a very real danger that some of them may be shunned because it is assumed that any young girl who was held was raped. I have spoken with other young women who escaped from Boko Haram on their own, and they told me that they were not. But I must say I wondered. When I was looking at the very many children and babies who came in this new group, I did wonder whose children those were.
TARGET: Is there one story that you heard from the women at the refugee camp who've been rescued - one story that has really stuck with you about what they endured?
```

**YOUR LABEL (F or N):** ______

### Row 43

```
PREV: Amy Howe of the blog Howe On The Court. Amy, thanks so much for taking the time on this holiday. We appreciate it.
GUEST: Thanks for inviting me. Take care.
TARGET: A Border Patrol officer was charged with fatally shooting a Mexican teenager over the U.S. border, and he has now been found not guilty of involuntary manslaughter.
```

**YOUR LABEL (F or N):** ______

### Row 44

```
PREV: Re-nominated. Do you think she can get confirmed this time?
GUEST: She could probably - well, I think that the right might vote against her. She is not predictable enough. But you know, she's certainly - she's still very busy. She hears cases on the Court of Appeals and is heavily promoting the idea that state supreme court justices should not be elected.
TARGET: Charles Evans Hughes.
```

**YOUR LABEL (F or N):** ______

### Row 45

```
PREV: Huh. What else were people looking for?
GUEST: ... that people didn't know how to spell it. So one of the things that we see online is the different attempts that are made. So they landed on ombre, O-M-B-R-E, which is the French word for shadow. It's also the name for, I think, a card game or something in English, which is why it's there. And also umber with a U, which is, of course, the color. And so they landed on these different pages kind of searching for the correct word, which reminds me of Aleppo. There's a combining form, lepo-, L-E-P-O, which people landed on because Aleppo is the name of a city, which is also in the dictionary, but people didn't know how to spell it.
TARGET: Ah. So people were just searching for lepo- instead of...
```

**YOUR LABEL (F or N):** ______

### Row 46

```
PREV: Rich Jaroslovsky is technology columnist for Bloomberg News. Thank you very much.
GUEST: Thank you.
TARGET: When the founder of Samsung passed away in the late 1980s, his assets were divided among his three children. Now, the youngest son, 70-year-old Chairman Lee Kun-hee of Samsung Electronics, is being sued by his older brother and sister.
```

**YOUR LABEL (F or N):** ______

### Row 47

```
PREV: ... when U.S. officials thought they might be making a mistake. It came in the 1970s. They feared Iran would become one of the nations then seeking nuclear weapons. U.S. diplomats began negotiating to limit Iran's nuclear program. And they discovered a problem still familiar to diplomats today. Iran insisted it had the same right to nuclear power as any nation.
GUEST: It's actually quite interesting that the shah famously said that unless it was clear that Iran was not being treated as a second-class country, he would look for alternative vendors and he will not work with U.S. companies to acquire nuclear technology for Iran.
TARGET: Chants, like this one. The shah was overthrown in 1979. Under the new Islamist government, thousands of people gathered at Tehran University each Friday. They angled their prayer mats toward Mecca. And at these prayers, Friday after Friday for decades, they have chanted death to America.
```

**YOUR LABEL (F or N):** ______

### Row 48

```
PREV: The United States supports the Yemeni government, considers it a vital partner in the fight against Al-Qaeda. How does the instability in the country right now complicate both the partnership with the U.S. and the fight against Al-Qaeda?
GUEST: Well, I think the question is absolutely right. I mean, it has complicated that fight. And it's, I think, also leading to questions about the strategy behind the counterterrorism campaign. At the moment, the United States finds itself supporting a president and a government that is growing weaker and weaker because of the turmoil and instability in the country. And the big question is what happens now? You know, I just returned from a month in Yemen. It feels really quite perilous there.
TARGET: Kareem Fahim is a Middle East correspondent for the New York Times, and he's just back from reporting in Yemen. Kareem, thanks very much.
```

**YOUR LABEL (F or N):** ______

### Row 49

```
PREV: Tony, thanks as always. We appreciate it.
GUEST: Thanks for having me.
TARGET: Right. I want to interrupt you, Steve, because we do have James Back on...
```

**YOUR LABEL (F or N):** ______

### Row 50

```
PREV: Now, the U.S. has made - has not been shy about calling Mugabe and Zimbabwe kind of rogue and outside of the interests of the U.S. What do you think the U.S. has at stake in this election?
GUEST: ... you know, discussions in the U.S. State Department using the term regime change after that term was actually placed on Iraq. We saw what happened in the case of Iraq. Regime change has led to disaster. Now when people hear regime change coming out of the State Department, there's a lot of worry about manipulation of processes, and so there is concern that the U.S. may not be playing fair, that there may be back-handed deals in which certain organizations are supported by the U.S., and these actually contribute to a climate of anxiety, where the U.S. and the U.K., even if they may be saying absolutely the right thing in this context, are not seen as really honest brokers.
TARGET: Now, briefly, what are the negotiations going on around that?
```

**YOUR LABEL (F or N):** ______

### Row 51

```
PREV: Right.
GUEST: There are a lot more civilians. It's second, third-biggest city in Iraq, really. So it's going to be a huge challenge.
TARGET: Well, Loveday Morris is the Baghdad bureau chief for The Washington Post. Thank you very much.
```

**YOUR LABEL (F or N):** ______

### Row 52

```
PREV: ... makes its debut in two weeks. But tonight it's already making headlines. And there's a TV special in the works. Joining me in Phoenix, Arizona is Fred Goldman, the father of Ron Goldman, who was brutally murdered. And, here in Los Angeles, Kim Goldman, Fred's daughter and Ron's sister. What was your first reaction, Fred, when you heard about this?
GUEST: Appalled. I don't know other -- there were a lot of other words but none of them we want to use on TV. It was amazing to me that this whole thing has gotten as far as it's gotten. Nothing would surprise me that this S.O.B. would do but the fact that someone is willing to publish this garbage that FOX is willing to put in on air, is just morally despicable to me.
TARGET: But they are all...
```

**YOUR LABEL (F or N):** ______

### Row 53

```
PREV: Well, where do you stand Kevin Trenberth? Do you expect that science may be put on trial by congressional committees?
GUEST: ... to be strong advocates for the science. And perhaps the issue here relates to what a scientist's comfort zone is. And many scientists are experts in relatively narrow areas. And as I get further on in my career, I've become broader and more general and more comfortable talking about other aspects. And so when one talks about a particular result and particular finding, you know, dealing with the implications of that and the ramifications of it and what happens if you do take certain kinds of actions in terms of the expectations and also if you don't, being able to talk about all of those kinds of things is perhaps - falls down to a relatively limited number of people.
TARGET: Well, why is it, Kevin, why is there such a gap between the public discourse and the science discourse on something like climate change? Why is there such a difference in what the public believe and what the - believes and what the general science community believes about it?
```

**YOUR LABEL (F or N):** ______

### Row 54

```
PREV: This chaos erupted just shortly after, in fact, the United States, among others, recognized the Transitional National Council as the legitimate government of Libya.
GUEST: That's in fact correct. Just a few days afterwards, and Britain and the United States have joined France and Turkey in recognizing the council. There are now some 20 countries that do. And the embarrassment is, of course - and is an embarrassment for NATO as well - that nobody knows whether there's really a workable organization there that could take over the administration of a country united after the civil war.
TARGET: And indeed there is doubt about delivering large supplies of unfrozen Libyan assets to such a fragile regime.
```

**YOUR LABEL (F or N):** ______

### Row 55

```
PREV: Who's shooting at you?
GUEST: It's not important, really, who's shooting at us. We honestly don't know. I mean, for us it doesn't make any difference who is shooting at us. I personally don't believe we are a direct target, but those are the calculated risks that I'm talking about. You know, when you're going somewhere, and you see a lot of military activities happening, then you decide - do I go there today, or do I come back tomorrow?
TARGET: The situation that you've described - how does this conflict compare to other conflict zones that you've worked in, in your career?
```

**YOUR LABEL (F or N):** ______

### Row 56

```
PREV: And I guess conclave is probably Latin as well.
GUEST: Same thing. I mean, so true for those - the terms of Catholic bureaucracy as you say. Those early Latin - the earliest Latin terms in the English language really did come from the church.
TARGET: Here's an email we have from Amy. Austerity, and she notes, I guess I wasn't paying attention in economics.
```

**YOUR LABEL (F or N):** ______

### Row 57

```
PREV: I'm just imagining somebody sitting in their car in traffic in Los Angeles listening to this conversation, wondering if they should be watching the skies for a missile coming over from North Korea.
GUEST: I hope that never happens.
TARGET: Well, everybody hopes it never happens. But you're the expert. Should they fear it happening?
```

**YOUR LABEL (F or N):** ______

### Row 58

```
PREV: Why don't you put this in some context, too, for the continent? Nigeria is not alone here. There are many, many other African countries that either outlaw homosexuality or persecute gay people, right?
GUEST: There are 39 African countries with laws against sodomy and homosexuality. And according to UNAIDS that is half of the countries in the world that criminalize homosexuality.
TARGET: Michelle Faul is chief Africa correspondent with the Associated Press. She joined us from Lagos, Nigeria. Michelle, thanks so much.
```

**YOUR LABEL (F or N):** ______

### Row 59

```
PREV: Frank La Salla is president of BNY Clearing International and joins us now with more. And Frank, in particular, good morning.
GUEST: Good morning.
TARGET: I'm wondering how it is that we get solid earnings when we're seeing a lot of warnings about the second half and a lot predictions about slowing economic growth?
```

**YOUR LABEL (F or N):** ______

### Row 60

```
PREV: So what does this disputed airspace symbolize?
GUEST: Well, there's two parts of this really. One is, is that the Japanese and Chinese are increasingly in contact with each other across the East China Sea. And that's your fisherman, its government agencies doing surveys for seabed resources and, of course, it's the two militaries. China and Japan however don't have an agreement on a maritime boundary. And this ADIZ that China announced on Saturday also puts the air space above the East China Sea in contest.
TARGET: So how seriously are people taking this latest diplomatic disagreement?
```

**YOUR LABEL (F or N):** ______


---

## Provenance

- Sampling seed: **62**. Rebuild this exact sheet with
  `.venv/bin/python experiments/h6_part2_tranche.py`.
- Rows: **60**, drawn from **5268** model classifications over
  **88** confirmatory subjects; **30** subjects appear.
- Classifier: Gemma-4-31B-it, rubric hash (frozen) `053b96cba42ebf03d966db3c22fce2acde3a685d5b4cca9badd556ee248a24da`
- Classifier records: `results/stage2_confirm/h6_classify/records/classify.jsonl`
- Answer key (do not open until finished):
  `results/stage2_openended/h6_part2_key.json`
