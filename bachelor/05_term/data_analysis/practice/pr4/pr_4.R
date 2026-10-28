df <- read.csv("life_exp.csv", sep = ";")
new_df <- df[,c(1, 2, 5, 17)]
colnames(new_df) <- c("state", "year", "y", "x")

library("knitr")
library("ggplot2")
library("plm")

h <- pdata.frame(new_df, index = c("state", "year"), row.names = T)

m.pooled <- plm(y ~ x, data = h, model = "pooling")
m.re <- plm(y ~ x, data = h, model = "random")
m.fe <- plm(y ~ x, data = h, model = "within")

summary(m.pooled)
summary(m.re)
summary(m.fe)

m.pooled.lm <- lm(y ~ x, data = h)
m.fe.lm <- lm(y ~ x + factor(state), data = h)

pFtest(m.fe, m.pooled)
plmtest(m.re, type = "bp")
fixef(m.fe)

sort(ranef(m.re))
