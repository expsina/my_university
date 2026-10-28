library(readxl)
library(ggplot2)
library(gridExtra)
library(psych)
library(car)

cw_data <- 
  read_excel("/Users/konstantinovivan/Desktop/КУРС_РАБ/6_семестр/Константинов/cw_data.xlsx",
             sheet = 1)
View(cw_data)

real_income <-
  data.frame(years = cw_data$years[20:29], 
             real_income_change = cw_data$real_income_change[20:29])

ggplot(data = real_income, mapping = aes(years, real_income_change)) + 
  geom_line(
    colour = "black",
    linewidth = 0.5) +
  geom_hline(yintercept = 100, 
             colour = "blue", 
             linewidth = .5) +
  labs(x = "Годы",
       y = "Реально располагаемые денежные доходы \n 
       в процентах к предыдущему году") +
  theme_bw()

ggsave("real_income.png",
       path = "/Users/konstantinovivan/Desktop/КУРС_РАБ/6_семестр/Константинов/graphs")

cf <-
  data.frame(years = cw_data$years[20:28], 
             gini_coef = cw_data$gini_coef[20:28])

View(cf)

ggplot(cf, aes(years, gini_coef)) +
  geom_line(
    colour = "black",
    linewidth = 0.5) +
  labs(x = "Годы",
       y = "Коэффициент Джини") +
  theme_bw()

ggsave("gini_coef.png",
       path = "/Users/konstantinovivan/Desktop/КУРС_РАБ/6_семестр/Константинов/graphs")

level <-
  data.frame(years = cw_data$years[20:28], 
             poor_level = cw_data$poor_level[20:28])


ggplot(level, aes(years, poor_level)) +
  geom_line(
    colour = "black",
    linewidth = 0.5) +
  labs(x = "Годы",
       y = "Численность населения с денежными доходами \n 
       ниже величины прожиточного минимума, %") +
  theme_bw()

ggsave("poor_level.png",
       path = "/Users/konstantinovivan/Desktop/КУРС_РАБ/6_семестр/Константинов/graphs")

income_types <- 
  read_excel("/Users/konstantinovivan/Desktop/КУРС_РАБ/6_семестр/cw_data.xlsx",
             sheet = 4)
colnames(income_types) <- c("type", "year", "value")

View(income_types)

struct_income <- grid.arrange(
  ggplot(data = income_types[income_types$year == 2008, ], aes(x = type, y = value)) +
    geom_col(fill = rgb(0/255, 0/255, 139/255)) +
    coord_flip() +
    ggtitle("Структура доходов в 2008 г.") +
    xlab("Виды дохода") +
    ylab("Доля от общего дохода, %") +
    geom_text(aes(label = value), hjust = 1.5, colour = "white") +
    theme_bw() +
    theme(axis.title.x = element_text(color = "black"),
          axis.title.y = element_text(color = "black"),
          axis.text.x = element_text(color = "black"),
          axis.text.y = element_text(color = "black")),
  ggplot(data = income_types[income_types$year == 2022, ], aes(x = type, y = value)) +
    geom_col(fill = rgb(0/255, 65/255, 106/255)) +
    coord_flip() +
    ggtitle("Структура доходов в 2022 г.") +
    xlab("Виды дохода") +
    ylab("Доля от общего дохода, %") +
    geom_text(aes(label = value), hjust = 1.5, colour = "white") +
    theme_bw()
)

ggsave("struct_income.png", 
       path = "/Users/konstantinovivan/Desktop/КУРС_РАБ/6_семестр/graphs",
       plot = struct_income)

cw_data <- 
  read_excel("/Users/konstantinovivan/Desktop/КУРС_РАБ/6_семестр/cw_data.xlsx",
             sheet = 5)
View(cw_data)

summary(cw_data)
describe(cw_data)

png(file = "/Users/konstantinovivan/Desktop/КУРС_РАБ/6_семестр/graphs/box_median_income.png")
boxplot(cw_data$median_income)
dev.off()

png(file = "/Users/konstantinovivan/Desktop/КУРС_РАБ/6_семестр/graphs/box_gov_income.png")
boxplot(cw_data$procent_gov_income)
dev.off()

boxplot(cw_data$count_dishwashers)


simon_data <- 
  read_excel("/Users/konstantinovivan/Desktop/КУРС_РАБ/6_семестр/Константинов/python/simon.xlsx",
             sheet = 1)
View(simon_data)

Boxplot