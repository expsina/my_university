d <- read.csv('heart.csv',sep= ',', dec = '.')
d <- na.omit(d)

d$gender <- factor(d$sex)
levels(d$gender) <- c('female', 'male')

View(d)
nd <- d[d$age >=55,]

t.test(nd$trtbps ~ nd$gender)

boxplot(nd$trtbps ~ nd$gender,
        data= nd, main="Test Scores by Group", xlab="Group", ylab="Score", col="green",
        border="black")
shapiro.test(nd$trtbps[nd$gender == 'female'])
shapiro.test(nd$trtbps[nd$gender == 'male'])

female = nd$trtbps[nd$gender == 'female'][1:length(nd$trtbps[nd$gender == 'male'])]
male = nd$trtbps[nd$gender == 'male'][1:length(nd$trtbps[nd$gender == 'female'])]

male1 <- male[male > (quantile(male, 0.25, na.rm = TRUE) - 1.5 * IQR(male, na.rm = TRUE)) & male < (quantile(male, 0.75, na.rm = TRUE) + 1.5 * IQR(male, na.rm = TRUE))]
female1 <- female[female > (quantile(female, 0.25, na.rm = TRUE) - 1.5 * IQR(female, na.rm = TRUE)) & female < (quantile(female, 0.75, na.rm = TRUE) + 1.5 * IQR(female, na.rm = TRUE))]

differences = female1[0:55] - male1[0:55]
shapiro.test(differences)

t.test(differences, mu = 0)

var.test(male1, female1)
