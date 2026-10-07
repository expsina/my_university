library(readxl)

data <- read_excel("data5.xlsx")
# set <- sample(1:10, 2) + 2
# set
# мы выбрали столбцы x1, x10

set <- c(3, 12)

dthr <- data[, c(set, 13)]

colnames(dthr) <- c("x10", "x1", "y")

dthr$y[dthr$y >= 1] <- 1
dthr$y[dthr$y < 1] <- 0

library(neuralnet)
library(ggplot2)
library(caret)

fit <- glm(dthr$y ~ dthr$x1 + dthr$x10 + dthr$x1:dthr$x10,
           dthr, family = "binomial")

summary(fit)

dthr$prob <- -396.8 + 395 * dthr$x1 + 535 * dthr$x10 + -533.1 * dthr$x1 * dthr$x10

dthr$yp <- exp(dthr$prob)/(1 + exp(dthr$prob))

dthr$yp[dthr$yp >= 0.5] <- 1
dthr$yp[dthr$yp < 0.5] <- 0

j = 0

for (i in 1:length(dthr$yp)){
  
  if (dthr$yp[i] == dthr$y[i]) {
    j = j + 1
  }
}

accuracy = j / length(dthr$yp)
accuracy

cm <- confusionMatrix(as.factor(dthr$y), as.factor(dthr$yp))
cm


iris <- data[, c(set, 13)]
colnames(iris) <- c("x1", "x10", "y")

ind <- sample(2, nrow(iris), replace = T, prob = c(0.7, 0.3))

trainset <- iris[ind == 1,]
testset <- iris[ind == 2,]

trainset$yt <- trainset$y <= 1
trainset$yf <- trainset$y > 1

trainset$x1 <- round(trainset$x1, 1)
trainset$x10 <- round(trainset$x10, 1)

net.iris <- neuralnet( (yt + yf) ~ x1 + x10, trainset, hidden = 2)

plot(net.iris)

net.iris$result.matrix

testset$x1 <- round(testset$x1, 1)
testset$x10 <- round(testset$x10, 1)

net.prob <- predict(net.iris, testset[,1:2])

for (i in 1:length(testset$y)) {
  if (testset$y[i] >= 0.5) {
    testset$y[i] = 1
  }
}

for (i in 1:length(testset$y)) {
  if (testset$y[i] < 0.5) {
    testset$y[i] = 0
  }
}

pred <- c(T, F)[apply(net.prob, 1, which.max)]

acc <- mean(pred == testset$y)
acc
