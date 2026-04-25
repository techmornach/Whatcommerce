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

when all these information is provided,
it asks the user what duration he'll like to pay for if its yearly or monthly
it then creates a user with that plan, but the user is still inactive
he asks the user i
then it creates a paystack link and sends it to the user asking him to pay
depending on the user response, if the user says he has paid, it tells the user to hold on as it is verifying payment

its the result of the paystack link webhook that activates the account
then depending on the result, the bot sends a message to the user tellim him what next

once verified

the next step would be to activate his account
to do this, the bot will explain for the user to connect a whatsapp account which would be his business whatsapp account, it would send a link that expires in 10 mins with a qr code, when he scans this qr code with his whatsapp, that whatsapp is connected as a store manager linked to his account,
this store manager must not be the whatsapp account used to communicate with the bot(i.e the user) and musn't be a user that the whatsapp account had created on the app
with this his account is activated

this user can then message this store manager to
create products, view products/product, delete product, edit product, create order, view orders, delete orders, list orders, view order,
the user can also make enquiries or calculations regarding his business and profits

for the earlier bot belonging to whatcommerce, not the store manager, the only thing the user can do is update his plan and delete is account, create users and set what permissions the user would have, delete users, edit users, list users and can even deactivate the store manager for customers, this is if he doesn't want the store manager to communicate with customers

now for the storemanager bot, if a user messages the bot, and this user isn't the super user, or a user created by the super user, this user is regarded a customer, he can view products, get recommendations, and make orders
for orders, the following are needed from the user, name, address and phone number
then the bot doesn't create the order, it sends a message to the a user with the ability to create orders, if this user doesn't exist, it sends a message to the super user, telling it to confirm the order, if the super user/user confirms the order then the order is created, the super admin can also send things like account details where to make payments, in fact the bot should ask the super admin how the user should make payment, the user could also reject the order and tell the bot why, which the bot uses to send a response back

but remember the moment a customer makes his first confirmed order, he is added in as a customer of that super user, this means when that order was created, it would a ciustomer id field
remember it only after an order is confirmed before it gets created

for the bots, we use openai agents sdk which would have access to serper for browsing, playwright mcp and tools available based on the user communicating with the

the whatcommerce bot would also have access to rag stated by the super admin

the storemanager bot would also have access to rag and creating and updating the rag or even deleting it, as the user can tell it things like its store policy e.t.c

for the api, we will use fast api

for the whatsapp server, we will use whatsapp web js not the official whatsapp api

for the frontend we use nextjs
