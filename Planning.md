Whatcommerce
this is an ecommerce platform to help small vendors and businesses manage their businesses from whatsapp
with a store manager who manager their business
this applicaiton has no free plan
it has three plans

lite: user can have 50 products, 2 users, 5000 naira a month
standard: user can have 100 products, 3 users, 10000 naira a month
premium: user can have 500 products, 5 users, 20000 naira a month

it is fully based on whatsapp

for the web app

it is a landing page, we have a get started button, that takes the user to a whatsapp chat
now for this whatsapp chat

we will have a super admin for the entire app

in the super admin dashboard we can view all users and their plan, expiry date
we can also setup the whatsapp bot, this is the whatsapp the user would be taken to on the landing page
we can also add knowledge base and faq for bots to use as rag

now when a user communicates with this bot, we first check, if this user is a user on the platform, if no, then we have a new user
we welcome the user to the platform, and ask if he'll like to get started with a plan, the agent would attend to any questions the user have, if the user is ready to get started with a plan,

it asks the user for the following information

- His name
- his business name
- and business address
- his email

when all these information is provided,
it asks the user what duration he'll like to pay for if its yearly or monthly
it then creates a user with that plan, but the user is still inactive
he asks the user i
then it creates a paystack link and sends it to the user asking him to pay
depending on the user response, if the user says he has paid, it tells the user to hold on as it is verifying payment

its the result of the paystack link webhook that activates the account
then depending on the result, the bot sends a message to the user tellim him what next

once verified he can now proceed to viewing products, creating products, deleting products, editing products, adding orders, editing orders e.t.c 
basically actions he would perform on a regular ecommerce erp platform, he can perform them through whatsapp
they can also do consulation based on their business, and even expoer their business infor into pdf, xlxs, e.t.c and even send voice notes

i plan on using openai agent sdk for agents, powered with serper for google search
i plan on using fast api for backend and uv
i plan on using whatsapp-web javascript package
and nextjs for frontend
paystack for payments

for the frontend

there would be a nice landing page, with get started which leads to the whatsapp bot

there is an admin page where the admin can view users, their subscriptions, also edit subscruption plans
the admin can also reconnect the whatsapp, since we are using whatsapp web not the official whatsapp business api
